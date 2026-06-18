"""Mapping helpers between NFH (DHP) payloads and Care domain objects."""

from datetime import date

from care.beckn.constants import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_BOOKING_CONFIRMED,
    LIFECYCLE_CANCELLED,
    LIFECYCLE_DRAFT,
    LIFECYCLE_FULFILLED,
    PARTICIPANT_ROLE_PATIENT,
    TXN_BOOKING,
    TXN_REFERRAL,
)
from care.emr.resources.patient.spec import GenderChoices
from care.emr.resources.resource_request.spec import StatusChoices

# NFH HealthParticipant.gender -> Care Patient.gender
GENDER_MAP = {
    "MALE": GenderChoices.male.value,
    "FEMALE": GenderChoices.female.value,
    "OTHER": GenderChoices.non_binary.value,
    "PREFER_NOT_TO_SAY": GenderChoices.non_binary.value,
}

# Care ResourceRequest.status -> NFH HealthReferral.lifecycleState
STATUS_TO_LIFECYCLE = {
    StatusChoices.pending.value: LIFECYCLE_DRAFT,
    StatusChoices.approved.value: LIFECYCLE_ACTIVE,
    StatusChoices.rejected.value: LIFECYCLE_CANCELLED,
    StatusChoices.cancelled.value: LIFECYCLE_CANCELLED,
    StatusChoices.transportation_to_be_arranged.value: LIFECYCLE_ACTIVE,
    StatusChoices.transfer_in_progress.value: LIFECYCLE_BOOKING_CONFIRMED,
    StatusChoices.completed.value: LIFECYCLE_FULFILLED,
}


def map_gender(nfh_gender: str | None) -> str:
    """Map an NFH gender code to a Care gender, defaulting to non_binary."""
    if not nfh_gender:
        return GenderChoices.non_binary.value
    return GENDER_MAP.get(nfh_gender.upper(), GenderChoices.non_binary.value)


def map_status_to_lifecycle(status: str | None) -> str:
    """Map a Care ResourceRequest status to an NFH lifecycleState."""
    if not status:
        return LIFECYCLE_DRAFT
    return STATUS_TO_LIFECYCLE.get(status, LIFECYCLE_DRAFT)


def get_contract(message: dict) -> dict:
    """Return the ``contract`` object from a Beckn message body."""
    return (message or {}).get("contract", {}) or {}


def get_contract_attributes(message: dict) -> dict:
    """Return the ``contractAttributes`` (NFH HealthReferral) from a message."""
    return get_contract(message).get("contractAttributes", {}) or {}


def get_coordination_id(context: dict, message: dict) -> str | None:
    """Return the referral correlation id from an inbound payload.

    For T1 (referral) this is ``coordinationId``; for T2 (booking) the same
    referral is referenced via ``coordinationRef``. Falls back to the contract
    id and finally the transaction id.
    """
    attributes = get_contract_attributes(message)
    return (
        attributes.get("coordinationId")
        or attributes.get("coordinationRef")
        or get_contract(message).get("id")
        or (context or {}).get("transactionId")
    )


def classify_transaction(context: dict, message: dict) -> str:
    """Classify an inbound payload as a referral (T1) or a booking (T2).

    The two transactions share the same endpoints, so they are told apart by
    the contract ``@type`` and the presence of ``coordinationRef`` (which only
    the downstream booking carries), with the ``networkId`` suffix as a hint.
    """
    attributes = get_contract_attributes(message)
    if attributes.get("coordinationRef"):
        return TXN_BOOKING
    contract_type = (attributes.get("@type") or "").lower()
    if "healthreferral" in contract_type:
        return TXN_REFERRAL
    if "healthcontract" in contract_type:
        return TXN_BOOKING
    network_id = (context or {}).get("networkId", "") or ""
    if network_id.endswith("-t2"):
        return TXN_BOOKING
    return TXN_REFERRAL


def find_patient_participant(message: dict) -> dict | None:
    """Locate the PATIENT participant within a Beckn contract message."""
    contract = get_contract(message)
    for participant in contract.get("participants", []) or []:
        attributes = participant.get("participantAttributes", {}) or {}
        if attributes.get("participantRole") == PARTICIPANT_ROLE_PATIENT:
            return participant
    return None


def extract_health_ids(participant: dict | None) -> list[dict]:
    """Extract ``healthIds`` ({system, value}) from a participant."""
    if not participant:
        return []
    attributes = participant.get("participantAttributes", {}) or {}
    return [
        {"system": item.get("system"), "value": item.get("value")}
        for item in attributes.get("healthIds", []) or []
        if item.get("value")
    ]


def extract_dob_and_age(
    participant: dict | None,
) -> tuple[date | None, int | None]:
    """Return ``(date_of_birth, age)`` from a participant's dateOfBirth."""
    if not participant:
        return None, None
    attributes = participant.get("participantAttributes", {}) or {}
    dob_value = attributes.get("dateOfBirth")
    if not dob_value:
        return None, None
    try:
        dob = date.fromisoformat(dob_value)
    except (TypeError, ValueError):
        return None, None
    return dob, None
