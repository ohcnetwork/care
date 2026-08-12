"""Consultation flow: Care as BAP requesting a specialist referral.

``discover`` broadcasts the referral need, ``select`` picks a coordinator offer
from the returned catalog, and ``confirm`` sends the patient data. On
``on_confirm`` a Care ``ResourceRequest`` (the durable referral record) is
created and linked back to the transaction.
"""

import logging

from care.beckn.builders.outbound import (
    build_context,
    build_discover_intent,
    build_patient_participant,
)
from care.beckn.constants import (
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_DRAFT,
    HEALTH_REFERRAL_CONTEXT,
    LIFECYCLE_ACTIVE,
)
from care.beckn.services.flows.base import FlowAdapter, FlowError

logger = logging.getLogger(__name__)

# JSON-LD schema context advertised on the consultation discover.
DISCOVER_SCHEMA_CONTEXT = (
    "https://schema.beckn.io/ServiceCoordinationResource/v2.1/context.jsonld"
)


def _referral_attributes(transaction_id: str, extra: dict | None = None) -> dict:
    attributes = {
        "@context": HEALTH_REFERRAL_CONTEXT,
        "@type": "hrf:HealthReferral",
        "coordinationId": transaction_id,
        "lifecycleState": LIFECYCLE_ACTIVE,
    }
    if extra:
        attributes.update(extra)
    return attributes


class ConsultationFlow(FlowAdapter):
    service_type = "consultation"

    def build_discover(self, transaction_id: str, routing: dict, query: dict) -> dict:
        """Broadcast the referral intent.

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
        """Select a coordinator offer returned in the ``on_discover`` catalog.

        The frontend may pass the entire catalog object (from ``on_discover``) as
        ``contract``.  The first offer id is extracted automatically from
        ``contract.offers[0].id``.  Alternatively ``offerId`` may be supplied
        directly.  BPP routing is managed by the frontend via ``context``
        overrides and the polling endpoint.
        """
        catalog = params.get("contract") or {}
        offers = catalog.get("offers") or []
        offer_id = (
            params.get("offerId")
            or params.get("offer_id")
            or (offers[0].get("id") if offers else None)
        )
        if not offer_id:
            raise FlowError("offerId is required to select a coordinator")
        contract = {
            "status": {"code": CONTRACT_STATUS_DRAFT},
            "commitments": [
                {
                    "id": f"commitment-{transaction_id}",
                    "status": {"descriptor": {"code": CONTRACT_STATUS_DRAFT}},
                    "offer": {"id": offer_id},
                }
            ],
            "contractAttributes": _referral_attributes(transaction_id),
        }
        return {
            "context": build_context("select", transaction_id, routing),
            "message": {"contract": contract},
        }

    def build_confirm(
        self, transaction_id: str, routing: dict, record: dict, params: dict
    ) -> dict:
        """Confirm the referral, carrying the patient participant."""
        offer_id = params.get("offerId") or params.get("offer_id")
        contract = {
            "status": {"code": CONTRACT_STATUS_ACTIVE},
            "descriptor": {"name": params.get("title") or "Care referral"},
            "commitments": [
                {
                    "id": f"commitment-{transaction_id}",
                    "status": {"descriptor": {"code": CONTRACT_STATUS_ACTIVE}},
                    "offer": {"id": offer_id} if offer_id else {},
                }
            ],
            "contractAttributes": _referral_attributes(transaction_id),
        }
        if params.get("reason"):
            contract["descriptor"]["shortDesc"] = params["reason"]
        participant = build_patient_participant(transaction_id, params)
        if participant:
            contract["participants"] = [participant]
        return {
            "context": build_context("confirm", transaction_id, routing),
            "message": {"contract": contract},
        }

    def on_confirmed(self, record: dict, message: dict) -> str | None:
        """Apply the ``on_confirm`` side effect for the consultation flow.

        When Care is also the BPP (loopback / single-instance deployment), the
        BPP has already created the ``ResourceRequest`` while handling the
        inbound ``init`` or ``confirm``. Here we just find that record — by
        contract id, else by coordination id — and mark it approved.

        When Care is a pure BAP (no local BPP), no record exists yet, so we
        fall through and create it directly with ``status=approved``.
        """
        from care.beckn.services.lookup import find_resource_request
        from care.emr.models.patient import Patient
        from care.emr.models.resource_request import ResourceRequest
        from care.emr.resources.resource_request.spec import (
            CategoryChoices,
            StatusChoices,
        )

        # Loopback path: the local BPP already created the record — find it and
        # mark it approved instead of creating a duplicate.
        existing = find_resource_request(record, message)
        if existing:
            self._apply_selected_patient(existing, record)
            if existing.status != StatusChoices.approved.value:
                existing.status = StatusChoices.approved.value
                existing.save(update_fields=["status", "modified_date"])
                logger.info(
                    "Consultation on_confirm: approved existing ResourceRequest %s",
                    existing.external_id,
                )
            else:
                logger.info(
                    "Consultation on_confirm: ResourceRequest %s already approved",
                    existing.external_id,
                )
            return str(existing.external_id)

        contract = (message or {}).get("contract", {}) or {}
        code = ((contract.get("status", {}) or {}).get("code") or "").upper()
        if code and code != CONTRACT_STATUS_ACTIVE:
            logger.info(
                "Consultation on_confirm not ACTIVE (code=%s); no referral created",
                code,
            )
            return None

        params = record.get("patient") or {}
        facility = self.resolve_confirm_facility(record)
        if facility is None:
            raise FlowError(
                "confirm did not carry a facility id (top-level 'facility' or "
                "contractAttributes.facilityId); cannot create referral"
            )
        patient = None
        if params.get("patient"):
            patient = Patient.objects.filter(external_id=params["patient"]).first()

        user = self._system_user()
        resource_request = ResourceRequest.objects.create(
            origin_facility=facility,
            related_patient=patient,
            title=(params.get("title") or "Care referral")[:255],
            reason=params.get("reason") or "",
            status=StatusChoices.approved.value,
            category=params.get("category") or CategoryChoices.other.value,
            created_by=user,
            updated_by=user,
            extensions={
                "beckn": {
                    "transactionId": record.get("transactionId"),
                    "coordinationId": record.get("transactionId"),
                    "contract": contract,
                }
            },
        )
        logger.info(
            "Consultation on_confirm created ResourceRequest %s",
            resource_request.external_id,
        )
        return str(resource_request.external_id)

    def on_lifecycle(self, record: dict, action: str, message: dict) -> str | None:
        """Apply a counterparty lifecycle callback to the local referral.

        A referral cancelled, progressed or completed by the BPP is reported back
        as ``on_status``/``on_update``/``on_cancel``; without this the Care record
        would sit at ``approved`` forever.
        """
        from care.beckn.services.lookup import find_resource_request

        referral = find_resource_request(record, message)
        if referral is None:
            logger.warning(
                "Beckn %s for transaction %s matched no referral; not applied",
                action,
                record.get("transactionId"),
            )
            return None
        return self.apply_referral_lifecycle(referral, action, message)

    @staticmethod
    def _apply_selected_patient(resource_request, record: dict) -> None:
        """Point the referral at the patient the frontend chose, if it differs.

        When Care is also the BPP, the referral was built from the confirm
        payload alone, so its patient may be one the BPP resolved (or created)
        from the contract rather than the record the frontend selected. Both
        sides are this instance, so the frontend's choice is authoritative.
        """
        from care.beckn.builders.outbound import resolve_patient

        patient = resolve_patient((record.get("patient") or {}).get("patient"))
        if patient is None or resource_request.related_patient_id == patient.id:
            return
        resource_request.related_patient = patient
        resource_request.save(update_fields=["related_patient", "modified_date"])
        logger.info(
            "Consultation on_confirm: referral %s moved to the selected patient %s",
            resource_request.external_id,
            patient.external_id,
        )
