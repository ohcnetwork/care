"""Per-action handlers for the BPP webhook.

Each handler receives the inbound Beckn ``context`` and ``message`` and returns
the corresponding ``on_*`` callback payload. ``init`` and ``confirm`` mutate
Care state (creating/approving a ``ResourceRequest``); ``select`` and
``status`` are read-only.
"""

from django.db import transaction

from care.beckn.builders.referral import (
    build_on_confirm,
    build_on_init,
    build_on_select,
    build_on_status,
)
from care.beckn.config import resolve_origin_facility
from care.beckn.mappers import (
    find_patient_participant,
    get_contract,
    get_contract_attributes,
)
from care.beckn.services.lookup import find_resource_request
from care.beckn.services.patient import find_or_create_patient
from care.emr.models.resource_request import ResourceRequest
from care.emr.resources.resource_request.spec import CategoryChoices, StatusChoices

# NFH clinicalUrgencyTier -> ResourceRequest priority (higher = more urgent).
URGENCY_PRIORITY = {
    "EMERGENCY": 3,
    "URGENT": 2,
    "ROUTINE": 1,
}


class BecknActionError(Exception):
    """Raised when an inbound action cannot be processed."""


def _resolve_system_user():
    from django.conf import settings

    from care.users.models import User

    username = getattr(settings, "BECKN_SYSTEM_USERNAME", None)
    if username:
        return User.objects.filter(username=username).first()
    return None


def _referral_fields(message: dict) -> dict:
    attributes = get_contract_attributes(message)
    contract = get_contract(message)
    urgency = attributes.get("clinicalUrgencyTier")
    target_criteria = attributes.get("targetCriteria", {}) or {}
    specialty = (target_criteria.get("specialty", {}) or {}).get("display") or (
        target_criteria.get("specialty", {}) or {}
    ).get("code")
    descriptor = contract.get("descriptor", {}) or {}
    title = descriptor.get("name") or (
        f"NFH Referral - {specialty}" if specialty else "NFH Referral"
    )
    consent = attributes.get("consent", {}) or {}
    reason = consent.get("clinicalJustification") or specialty or ""
    return {
        "title": title[:255],
        "reason": reason,
        "emergency": urgency == "EMERGENCY",
        "priority": URGENCY_PRIORITY.get(urgency),
        "category": CategoryChoices.patient_care.value,
    }


def handle_select(context: dict, message: dict) -> dict:
    """Echo the selected offer (no state change)."""
    return build_on_select(context, message)


def handle_init(context: dict, message: dict) -> dict:
    """Create the patient and a pending ResourceRequest, return on_init."""
    facility = resolve_origin_facility(context, message)
    if facility is None:
        raise BecknActionError(
            "No facility id in payload (contractAttributes.facilityId) "
            "matched a Care facility"
        )

    user = _resolve_system_user()
    contract = get_contract(message)
    attributes = get_contract_attributes(message)
    coordination_id = attributes.get("coordinationId") or contract.get("id")
    transaction_id = (context or {}).get("transactionId")

    with transaction.atomic():
        participant = find_patient_participant(message)
        patient = find_or_create_patient(message, participant, facility, user)

        fields = _referral_fields(message)
        resource_request = ResourceRequest(
            origin_facility=facility,
            related_patient=patient,
            status=StatusChoices.pending.value,
            created_by=user,
            updated_by=user,
            **fields,
        )
        resource_request.extensions = {
            "beckn": {
                "coordinationId": coordination_id,
                "transactionId": transaction_id,
                "contract": contract,
                "contractAttributes": attributes,
                "participants": contract.get("participants", []),
            }
        }
        resource_request.save()

    return build_on_init(context, message, resource_request)


def handle_confirm(context: dict, message: dict) -> dict:
    """Approve the referral and return on_confirm."""
    resource_request = find_resource_request(context, message)
    if resource_request is None:
        raise BecknActionError("Referral not found for confirm")

    contract = get_contract(message)
    attributes = get_contract_attributes(message)
    with transaction.atomic():
        resource_request.status = StatusChoices.approved.value
        extensions = resource_request.extensions or {}
        beckn = extensions.setdefault("beckn", {})
        # Persist the confirmed contract snapshot for status callbacks.
        beckn["contract"] = contract or beckn.get("contract")
        beckn["contractAttributes"] = attributes or beckn.get("contractAttributes")
        if attributes.get("consent"):
            beckn["consent"] = attributes["consent"]
        if contract.get("participants"):
            beckn["participants"] = contract["participants"]
        resource_request.extensions = extensions
        resource_request.save()

    return build_on_confirm(context, message, resource_request)


def handle_status(context: dict, message: dict) -> dict:
    """Return the current referral state as on_status."""
    resource_request = find_resource_request(context, message)
    if resource_request is None:
        raise BecknActionError("Referral not found for status")
    return build_on_status(context, message, resource_request)


ACTION_HANDLERS = {
    "select": handle_select,
    "init": handle_init,
    "confirm": handle_confirm,
    "status": handle_status,
}
