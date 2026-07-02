"""Builder for the outbound resource-request referral confirm (Care as BAP).

When a Care ``ResourceRequest`` in ``pending``/``other`` is created, Care acts as
a Beckn BAP and sends a ``confirm`` to an external coordination center (CC) that
acts as the BPP. This module builds that ``{context, message}`` payload from the
resource request, following the NFH ``HealthReferral`` contract shape.
"""

import uuid

from django.conf import settings
from django.utils import timezone

from care.beckn.constants import (
    CODED_VALUE_CONTEXT,
    CONTRACT_STATUS_ACTIVE,
    HEALTH_PARTICIPANT_CONTEXT,
    HEALTH_REFERRAL_CONTEXT,
    LIFECYCLE_ACTIVE,
    PARTICIPANT_ROLE_PATIENT,
)
from care.emr.resources.resource_request.spec import CategoryChoices

# ResourceRequest.priority at or above this level maps to an URGENT tier.
URGENT_PRIORITY_THRESHOLD = 2


# Care ResourceRequest urgency -> NFH clinicalUrgencyTier.
def _clinical_urgency_tier(resource_request) -> str:
    if resource_request.emergency:
        return "EMERGENCY"
    if (
        resource_request.priority
        and resource_request.priority >= URGENT_PRIORITY_THRESHOLD
    ):
        return "URGENT"
    return "ROUTINE"


# Care ResourceRequest category -> NFH targetCriteria. ``patient_care``
# referrals additionally carry the field-visit procedure needs and an in-person
# consultation modality.
def _target_criteria(resource_request) -> dict:
    criteria = {
        # Required by the HealthReferral schema when lifecycleState is ACTIVE.
        # serviceCategory.code must be one of the network-allowed values:
        # ADMISSION, CONSULTATION, INVESTIGATION, PROCEDURE.
        "serviceCategory": {
            "@context": CODED_VALUE_CONTEXT,
            "@type": "ServiceCategory",
            "code": "INVESTIGATION",
            "display": "Investigation",
        },
    }
    if resource_request.category == CategoryChoices.patient_care.value:
        criteria["serviceCategory"] = {
            "@context": CODED_VALUE_CONTEXT,
            "@type": "ServiceCategory",
            "code": "CONSULTATION",
            "display": "Consultation",
        }
        criteria["procedureNeeds"] = ["HOME_VISIT"]
        criteria["consultationModality"] = "IN_PERSON"
    return criteria


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
        "contractAttributes": {
            "@context": HEALTH_REFERRAL_CONTEXT,
            "@type": "hrf:HealthReferral",
            "coordinationId": str(rr.external_id),
            "lifecycleState": LIFECYCLE_ACTIVE,
            "clinicalUrgencyTier": _clinical_urgency_tier(rr),
            "targetCriteria": _target_criteria(rr),
        },
    }
    if rr.reason:
        contract["descriptor"]["shortDesc"] = rr.reason
    if rr.related_patient_id:
        contract["participants"] = [_patient_participant(rr.related_patient)]

    return {
        "context": build_confirm_context(transaction_id),
        "message": {"contract": contract},
    }
