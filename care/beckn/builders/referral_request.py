"""Builder for the outbound resource-request referral confirm (Care as BAP).

When a Care ``ResourceRequest`` in a referral category is created, Care acts as a
Beckn BAP and sends a ``confirm`` to an external coordination center (CC) that
acts as the BPP. This module builds that ``{context, message}`` payload from the
resource request, following the NFH ``HealthReferral`` contract shape.

For care-to-care transactions the counterparty BPP is another Care instance: the
contract carries the target facility id (``contractAttributes.facilityId``) so
the receiving Care can attach its own ``ResourceRequest`` to a known facility,
and the context carries this Care's BAP id/uri so the CC can route the eventual
completion ``update`` back here.
"""

import uuid

from django.conf import settings
from django.utils import timezone

from care.beckn.constants import (
    CODED_VALUE_CONTEXT,
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_COMPLETED,
    HEALTH_PARTICIPANT_CONTEXT,
    HEALTH_REFERRAL_CONTEXT,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_FULFILLED,
    PARTICIPANT_ROLE_PATIENT,
)
from care.emr.resources.resource_request.spec import CategoryChoices

# ResourceRequest.priority at or above this level maps to an URGENT tier.
URGENT_PRIORITY_THRESHOLD = 2


def _clinical_urgency_tier(resource_request) -> str:
    """Map Care ResourceRequest urgency -> NFH clinicalUrgencyTier."""
    if resource_request.emergency:
        return "EMERGENCY"
    if (
        resource_request.priority
        and resource_request.priority >= URGENT_PRIORITY_THRESHOLD
    ):
        return "URGENT"
    return "ROUTINE"


def _target_criteria(resource_request) -> dict:
    """Map category -> NFH targetCriteria.

    ``patient_care`` is a downward field/consultation referral; every other
    category is treated as an upward investigation (lab) referral.
    """
    if resource_request.category == CategoryChoices.patient_care.value:
        return {
            "serviceCategory": {
                "@context": CODED_VALUE_CONTEXT,
                "@type": "ServiceCategory",
                "code": "CONSULTATION",
                "display": "Consultation",
            },
            "procedureNeeds": ["HOME_VISIT"],
            "consultationModality": "IN_PERSON",
        }
    return {
        "serviceCategory": {
            "@context": CODED_VALUE_CONTEXT,
            "@type": "ServiceCategory",
            "code": "INVESTIGATION",
            "display": "Investigation",
        },
    }


def _confirm_facility_external_id(resource_request) -> str | None:
    """The facility id the receiving Care should attach its referral to.

    Prefer the request's ``assigned_facility`` (the target chosen by the
    referrer, which exists in the counterparty Care instance); fall back to the
    origin facility for single-instance/loopback deployments.
    """
    rr = resource_request
    if rr.assigned_facility_id:
        return str(rr.assigned_facility.external_id)
    if rr.origin_facility_id:
        return str(rr.origin_facility.external_id)
    return None


def build_confirm_context(transaction_id: str) -> dict:
    """Build the outbound ``confirm`` context from configured BAP/CC identity."""
    return {
        "networkId": getattr(settings, "BECKN_NETWORK_ID", "") or None,
        "action": "confirm",
        "version": getattr(settings, "BECKN_VERSION", "2.0.0"),
        "bapId": getattr(settings, "BECKN_BAP_ID", "") or None,
        "bapUri": getattr(settings, "BECKN_BAP_URI", "") or None,
        "transactionId": transaction_id,
        "messageId": str(uuid.uuid4()),
        "timestamp": timezone.now().isoformat(),
        "bppId": getattr(settings, "BECKN_CC_BPP_ID", "") or None,
        "bppUri": getattr(settings, "BECKN_CC_BPP_URI", "") or None,
    }


def _patient_participant(patient) -> dict:
    return {
        "id": f"participant-patient-{patient.external_id}",
        "descriptor": {"name": patient.name},
        "participantAttributes": {
            "@context": HEALTH_PARTICIPANT_CONTEXT,
            "@type": "hpa:HealthParticipant",
            "participantRole": PARTICIPANT_ROLE_PATIENT,
        },
    }


def build_referral_confirm(resource_request, transaction_id: str) -> dict:
    """Build the outbound ``confirm`` payload for a Care ``ResourceRequest``."""
    rr = resource_request
    attributes = {
        "@context": HEALTH_REFERRAL_CONTEXT,
        "@type": "hrf:HealthReferral",
        "coordinationId": str(rr.external_id),
        "lifecycleState": LIFECYCLE_ACTIVE,
        "clinicalUrgencyTier": _clinical_urgency_tier(rr),
        "targetCriteria": _target_criteria(rr),
    }
    facility_id = _confirm_facility_external_id(rr)
    if facility_id:
        attributes["facilityId"] = facility_id
    if rr.origin_facility_id:
        attributes["originFacilityId"] = str(rr.origin_facility.external_id)

    contract = {
        "status": {"code": CONTRACT_STATUS_ACTIVE},
        "descriptor": {"name": rr.title},
        "commitments": [
            {
                "id": f"commitment-{rr.external_id}",
                "status": {"descriptor": {"code": CONTRACT_STATUS_ACTIVE}},
                "resources": [{"id": str(rr.external_id), "quantity": {"count": 1}}],
                "offer": {
                    "id": f"offer-{rr.external_id}",
                    "resourceIds": [str(rr.external_id)],
                },
            }
        ],
        "contractAttributes": attributes,
    }
    if rr.reason:
        contract["descriptor"]["shortDesc"] = rr.reason
    if rr.related_patient_id:
        contract["participants"] = [_patient_participant(rr.related_patient)]

    return {
        "context": build_confirm_context(transaction_id),
        "message": {"contract": contract},
    }


def build_referral_update_callback(resource_request) -> dict | None:
    """Build the ``on_update`` completion callback to the origin BAP.

    Care-to-care: once the assigned-side request is fulfilled, the origin Care
    (which sent the confirm) is notified so it can complete its own request. The
    origin's BAP routing and request id were stored on ``extensions['beckn']``
    at confirm time. Returns ``None`` when no origin routing is present (a
    loopback or non-Beckn request), so the caller can skip delivery.
    """
    beckn = (resource_request.extensions or {}).get("beckn") or {}
    routing = beckn.get("returnRouting") or {}
    bap_id = routing.get("bapId")
    bap_uri = routing.get("bapUri")
    if not (bap_id and bap_uri):
        return None
    coordination_id = beckn.get("originResourceRequestId") or beckn.get(
        "coordinationId"
    )
    context = {
        "networkId": getattr(settings, "BECKN_NETWORK_ID", "") or None,
        "action": "on_update",
        "version": getattr(settings, "BECKN_VERSION", "2.0.0"),
        "bapId": bap_id,
        "bapUri": bap_uri,
        "bppId": getattr(settings, "BECKN_BPP_ID", "") or None,
        "bppUri": getattr(settings, "BECKN_BPP_URI", "") or None,
        "transactionId": coordination_id,
        "messageId": str(uuid.uuid4()),
        "timestamp": timezone.now().isoformat(),
    }
    contract = {
        "status": {"code": CONTRACT_STATUS_COMPLETED},
        "contractAttributes": {
            "@context": HEALTH_REFERRAL_CONTEXT,
            "@type": "hrf:HealthReferral",
            "coordinationId": coordination_id,
            "lifecycleState": LIFECYCLE_FULFILLED,
        },
    }
    return {"context": context, "message": {"contract": contract}}
