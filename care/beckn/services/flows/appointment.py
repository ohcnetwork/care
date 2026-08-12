"""Appointment flow: Care as BAP booking an appointment with a remote BPP.

Mirrors the consultation flow but uses the NFH ``HealthContract`` appointment
shape: ``discover`` finds bookable providers, ``select`` picks a slot/offer, and
``confirm`` books it carrying the patient. The booking itself lives on the remote
BPP; locally the confirmed contract is recorded against the referral it fulfils,
or against a ``ResourceRequest`` created for it, so it outlives the in-flight
transaction record in Redis.
"""

import logging

from care.beckn.builders.outbound import (
    build_context,
    build_discover_intent,
    build_patient_participant,
    resolve_patient,
)
from care.beckn.constants import (
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_DRAFT,
    HEALTH_CONTRACT_CONTEXT,
)
from care.beckn.services.flows.base import FlowAdapter, FlowError

logger = logging.getLogger(__name__)

# JSON-LD schema context advertised on the appointment discover.
DISCOVER_SCHEMA_CONTEXT = "https://schema.beckn.io/HealthResource/v2.1/context.jsonld"


def _appointment_attributes(extra: dict | None = None) -> dict:
    attributes = {
        "@context": HEALTH_CONTRACT_CONTEXT,
        "@type": "hct:HealthContract",
        "healthServiceType": "PHYSICAL_CONSULTATION",
    }
    if extra:
        attributes.update(extra)
    return attributes


class AppointmentFlow(FlowAdapter):
    service_type = "appointment"

    def build_discover(self, transaction_id: str, routing: dict, query: dict) -> dict:
        """Broadcast the appointment intent.

        ``query`` may carry ``healthServiceType`` (→ JSONPath catalog filter),
        ``textSearch`` or a ready-made ``filters`` object.
        """
        return {
            "context": build_context(
                "discover",
                transaction_id,
                routing,
                {"schemaContext": [DISCOVER_SCHEMA_CONTEXT]},
            ),
            "message": {"intent": build_discover_intent(query)},
        }

    def build_select(
        self, transaction_id: str, routing: dict, record: dict, params: dict
    ) -> dict:
        offer_id = params.get("offerId") or params.get("offer_id")
        if not offer_id:
            raise FlowError("offerId is required to select an appointment slot")
        contract = {
            "status": {"code": CONTRACT_STATUS_DRAFT},
            "commitments": [
                {
                    "id": f"commitment-{transaction_id}",
                    "status": {"descriptor": {"code": CONTRACT_STATUS_DRAFT}},
                    "offer": {"id": offer_id},
                }
            ],
            "contractAttributes": _appointment_attributes(),
        }
        if params.get("slotId"):
            contract["performance"] = [{"slotId": params["slotId"]}]
        return {
            "context": build_context("select", transaction_id, routing),
            "message": {"contract": contract},
        }

    def build_confirm(
        self, transaction_id: str, routing: dict, record: dict, params: dict
    ) -> dict:
        offer_id = params.get("offerId") or params.get("offer_id")
        contract = {
            "status": {"code": CONTRACT_STATUS_ACTIVE},
            "commitments": [
                {
                    "id": f"commitment-{transaction_id}",
                    "status": {"descriptor": {"code": CONTRACT_STATUS_ACTIVE}},
                    "offer": {"id": offer_id} if offer_id else {},
                }
            ],
            "contractAttributes": _appointment_attributes(),
        }
        if params.get("slotId"):
            contract["performance"] = [{"slotId": params["slotId"]}]
        participant = build_patient_participant(transaction_id, params)
        if participant:
            contract["participants"] = [participant]
        return {
            "context": build_context("confirm", transaction_id, routing),
            "message": {"contract": contract},
        }

    def on_confirmed(self, record: dict, message: dict) -> str | None:
        """Persist the appointment the remote BPP confirmed.

        The booking itself lives at the provider, so what is kept locally is the
        confirmed contract: on the referral the appointment was booked against
        when the confirm named one (``coordinationRef``), otherwise on a
        ``ResourceRequest`` created for it. Without this the appointment exists
        only as the Redis transaction record and disappears with its 24h TTL.
        """
        from care.emr.models.resource_request import ResourceRequest
        from care.emr.resources.resource_request.spec import (
            CategoryChoices,
            StatusChoices,
        )

        contract = (message or {}).get("contract", {}) or {}
        code = ((contract.get("status") or {}).get("code") or "").upper()
        confirmed = code != CONTRACT_STATUS_DRAFT

        referral = self._linked_referral(record, message)
        if referral is not None:
            return self._record_appointment_on_referral(
                referral, record, contract, confirmed=confirmed
            )

        params = record.get("patient") or {}
        facility = self.resolve_confirm_facility(record)
        if facility is None:
            logger.error(
                "Beckn appointment confirmed remotely for transaction %s but "
                "neither a referral (contractAttributes.coordinationRef) nor a "
                "facility was named; nothing could be persisted",
                record.get("transactionId"),
            )
            return None

        user = self._system_user()
        resource_request = ResourceRequest.objects.create(
            origin_facility=facility,
            related_patient=resolve_patient(params.get("patient")),
            title=(params.get("title") or "Remote appointment")[:255],
            reason=params.get("reason") or "",
            status=(
                StatusChoices.transfer_in_progress.value
                if confirmed
                else StatusChoices.approved.value
            ),
            category=params.get("category") or CategoryChoices.other.value,
            created_by=user,
            updated_by=user,
            extensions={
                "beckn": {
                    "transactionId": record.get("transactionId"),
                    "coordinationId": record.get("transactionId"),
                    "appointment": contract,
                }
            },
        )
        logger.info(
            "Appointment on_confirm created ResourceRequest %s for the remote booking",
            resource_request.external_id,
        )
        return str(resource_request.external_id)

    def on_lifecycle(self, record: dict, action: str, message: dict) -> str | None:
        """Apply a remote provider's lifecycle callback to the local record."""
        referral = self._linked_referral(record, message)
        if referral is None:
            logger.warning(
                "Beckn %s for transaction %s matched no local appointment record; "
                "not applied",
                action,
                record.get("transactionId"),
            )
            return None
        return self.apply_referral_lifecycle(referral, action, message)

    @staticmethod
    def _linked_referral(record: dict, message: dict):
        """Find the local record this remote appointment belongs to.

        Either the record created for it on a previous callback
        (``resourceRequestId``) or the referral the appointment was booked
        against, named by ``coordinationRef`` on the echoed contract or on the
        confirm Care sent.
        """
        from care.beckn.mappers import get_coordination_ref
        from care.beckn.services import txn_store
        from care.beckn.services.lookup import (
            find_resource_request_by_coordination_id,
            find_resource_request_by_external_id,
        )

        existing = find_resource_request_by_external_id(record.get("resourceRequestId"))
        if existing is not None:
            return existing

        coordination_ref = get_coordination_ref(message)
        if not coordination_ref:
            sent_confirm = (
                txn_store.get_action(record.get("transactionId"), "CONFIRM") or {}
            )
            coordination_ref = get_coordination_ref(sent_confirm.get("message") or {})
        return find_resource_request_by_coordination_id(coordination_ref)

    @staticmethod
    def _record_appointment_on_referral(
        referral, record: dict, contract: dict, *, confirmed: bool
    ) -> str:
        """Snapshot the remote appointment onto the referral it fulfils.

        A confirmed appointment also advances the referral to
        ``transfer_in_progress`` (reported to the network as
        ``BOOKING_CONFIRMED``); one still awaiting a coordinator's review
        (``DRAFT``) only stores the snapshot.
        """
        from care.emr.resources.resource_request.spec import StatusChoices

        extensions = referral.extensions or {}
        beckn = extensions.setdefault("beckn", {})
        beckn["appointment"] = contract
        beckn["appointmentTransactionId"] = record.get("transactionId")
        referral.extensions = extensions

        fields = ["extensions", "modified_date"]
        if confirmed and referral.status in (
            StatusChoices.pending.value,
            StatusChoices.approved.value,
        ):
            referral.status = StatusChoices.transfer_in_progress.value
            fields.append("status")
        referral.save(update_fields=fields)
        logger.info(
            "Appointment on_confirm recorded on referral %s (status=%s)",
            referral.external_id,
            referral.status,
        )
        return str(referral.external_id)
