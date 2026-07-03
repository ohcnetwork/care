"""Consultation flow: Care as BAP requesting a specialist referral.

``discover`` broadcasts the referral need, ``select`` picks a coordinator offer
from the returned catalog, and ``confirm`` sends the patient data. On
``on_confirm`` a Care ``ResourceRequest`` (the durable referral record) is
created and linked back to the transaction.
"""

import logging

from care.beckn.builders.outbound import build_context, build_discover_intent
from care.beckn.constants import (
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_DRAFT,
    HEALTH_PARTICIPANT_CONTEXT,
    HEALTH_REFERRAL_CONTEXT,
    LIFECYCLE_ACTIVE,
    PARTICIPANT_ROLE_PATIENT,
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
        """Select a coordinator offer returned in the ``on_discover`` catalog."""
        offer_id = params.get("offerId") or params.get("offer_id")
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
        patient_name = params.get("patientName") or params.get("patient_name")
        if patient_name:
            contract["participants"] = [
                {
                    "id": f"participant-patient-{transaction_id}",
                    "descriptor": {"name": patient_name},
                    "participantAttributes": {
                        "@context": HEALTH_PARTICIPANT_CONTEXT,
                        "@type": "hpa:HealthParticipant",
                        "participantRole": PARTICIPANT_ROLE_PATIENT,
                    },
                }
            ]
        return {
            "context": build_context("confirm", transaction_id, routing),
            "message": {"contract": contract},
        }

    def on_confirmed(self, record: dict, message: dict) -> str | None:
        """Create the durable ``ResourceRequest`` referral for a confirmed exchange."""
        from care.emr.models.patient import Patient
        from care.emr.models.resource_request import ResourceRequest
        from care.emr.resources.resource_request.spec import (
            CategoryChoices,
            StatusChoices,
        )
        from care.facility.models import Facility

        contract = (message or {}).get("contract", {}) or {}
        code = ((contract.get("status", {}) or {}).get("code") or "").upper()
        if code and code != CONTRACT_STATUS_ACTIVE:
            logger.info(
                "Consultation on_confirm not ACTIVE (code=%s); no referral created",
                code,
            )
            return None

        params = record.get("patient") or {}
        # Resolve the origin facility either from an explicit confirm field or,
        # in passthrough mode, from the sent contract's contractAttributes.
        facility_external_id = params.get("facility")
        if not facility_external_id:
            from care.beckn.services import txn_store

            sent_confirm = (
                txn_store.get_action(record.get("transactionId"), "CONFIRM") or {}
            )
            sent_attributes = (sent_confirm.get("message") or {}).get(
                "contract", {}
            ).get("contractAttributes", {}) or {}
            facility_external_id = sent_attributes.get("facilityId")
        facility = Facility.objects.filter(external_id=facility_external_id).first()
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

    @staticmethod
    def _system_user():
        from django.conf import settings

        from care.users.models import User

        username = getattr(settings, "BECKN_SYSTEM_USERNAME", None)
        if username:
            return User.objects.filter(username=username).first()
        return None
