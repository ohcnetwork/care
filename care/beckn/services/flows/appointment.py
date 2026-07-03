"""Appointment flow: Care as BAP booking an appointment with a remote BPP.

Mirrors the consultation flow but uses the NFH ``HealthContract`` appointment
shape: ``discover`` finds bookable providers, ``select`` picks a slot/offer, and
``confirm`` books it carrying the patient. The confirmed appointment lives on the
remote BPP, so there is no local domain object to create on ``on_confirm`` (the
transaction record in Redis is the frontend's source of truth).
"""

import logging

from care.beckn.builders.outbound import build_context, build_discover_intent
from care.beckn.constants import (
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_DRAFT,
    HEALTH_CONTRACT_CONTEXT,
    HEALTH_PARTICIPANT_CONTEXT,
    PARTICIPANT_ROLE_PATIENT,
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
