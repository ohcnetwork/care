"""Mapping helpers between NFH (DHP) payloads and Care domain objects."""

from datetime import date

from care.beckn.constants import (
    FLOW_APPOINTMENT,
    FLOW_REFERRAL,
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
    # Transgender referrals are recorded as Care's "other" gender.
    "TRANSGENDER": GenderChoices.non_binary.value,
}

# Care Patient.gender -> NFH HealthParticipant.gender. The NFH/ONIX schema only
# accepts MALE/FEMALE/OTHER/PREFER_NOT_TO_SAY, so Care's non_binary and
# transgender both map to OTHER on the way out.
GENDER_TO_NFH = {
    GenderChoices.male.value: "MALE",
    GenderChoices.female.value: "FEMALE",
    GenderChoices.non_binary.value: "OTHER",
    GenderChoices.transgender.value: "OTHER",
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
        return GenderChoices.male.value
    return GENDER_MAP.get(nfh_gender.upper(), GenderChoices.male.value)


def map_gender_to_nfh(care_gender: str | None) -> str:
    """Map a Care gender to an NFH/ONIX gender code, defaulting to OTHER."""
    if not care_gender:
        return "MALE"
    return GENDER_TO_NFH.get(care_gender, "MALE")


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


def resolve_flow(action: str, context: dict, message: dict) -> str:
    """Route an inbound shared action to the referral or appointment flow.

    The referral flow (T1/T2) drives a Care ``ResourceRequest``; the appointment
    flow drives the Care scheduling system. ``select``/``init``/``confirm``/
    ``status``/``cancel`` are shared between both, so the flow is resolved from
    the contract discriminator, falling back to a stored-record lookup for thin
    payloads (e.g. a ``status`` carrying only ``contract.id``).
    """
    if action == "discover":
        return FLOW_APPOINTMENT

    attributes = get_contract_attributes(message)
    contract_type = (attributes.get("@type") or "").lower()
    if "healthreferral" in contract_type:
        return FLOW_REFERRAL
    if "healthcontract" in contract_type or attributes.get("healthServiceType"):
        return FLOW_APPOINTMENT
    # The downstream referral booking (T2) references the T1 referral.
    if attributes.get("coordinationRef"):
        return FLOW_REFERRAL

    # Thin payload (only contract.id): resolve against persisted records.
    return _resolve_flow_by_lookup(context, message)


def _resolve_flow_by_lookup(context: dict, message: dict) -> str:
    """Resolve the flow for a thin payload by matching a persisted record.

    A Care ``TokenBooking`` whose ``external_id`` matches the inbound contract
    id implies the appointment flow; otherwise an existing ``ResourceRequest``
    implies the referral flow. Defaults to the referral flow when neither
    matches, preserving the historical behaviour.
    """
    contract_id = get_contract(message).get("id")
    if contract_id:
        from care.emr.models.scheduling.booking import TokenBooking

        if TokenBooking.objects.filter(external_id=contract_id).exists():
            return FLOW_APPOINTMENT

    from care.beckn.services.lookup import find_resource_request

    if find_resource_request(context, message) is not None:
        return FLOW_REFERRAL
    return FLOW_REFERRAL


def get_selected_resource_id(message: dict) -> str | None:
    """Return the selected resource id from a contract's first commitment."""
    contract = get_contract(message)
    for commitment in contract.get("commitments", []) or []:
        for resource in commitment.get("resources", []) or []:
            resource_id = resource.get("id")
            if resource_id:
                return resource_id
    return None


def get_selected_slot_id(message: dict) -> str | None:
    """Return the chosen Care ``TokenSlot`` id carried on the contract.

    The slot id rides on the first performance entry (preferred) or, failing
    that, the first commitment id, so the chosen slot survives the
    select -> init -> confirm round trip without protocol changes.
    """
    contract = get_contract(message)
    for performance in contract.get("performance", []) or []:
        slot_id = performance.get("slotId") or performance.get("id")
        if slot_id:
            return slot_id
    for commitment in contract.get("commitments", []) or []:
        slot_id = commitment.get("slotId")
        if slot_id:
            return slot_id
    return None


def get_confirmed_appointment_time(message: dict) -> str | None:
    """Return the confirmed appointment time from the first performance entry."""
    contract = get_contract(message)
    for performance in contract.get("performance", []) or []:
        attributes = performance.get("performanceAttributes", {}) or {}
        confirmed = attributes.get("confirmedAppointmentTime") or attributes.get(
            "appointmentWindowStart"
        )
        if confirmed:
            return confirmed
    return None


def get_requested_date(context: dict, message: dict) -> str | None:
    """Return the requested appointment date (ISO date) from the payload.

    Read from the intent's preferred window, the first performance window, or
    the context timestamp, in that order.
    """
    message = message or {}
    intent = message.get("intent", {}) or {}
    preferred = intent.get("preferredDate") or intent.get("date")
    if preferred:
        return preferred
    contract = get_contract(message)
    for performance in contract.get("performance", []) or []:
        attributes = performance.get("performanceAttributes", {}) or {}
        window_start = attributes.get("appointmentWindowStart")
        if window_start:
            return window_start
    return (context or {}).get("timestamp")


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
