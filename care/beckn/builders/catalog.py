"""Builders for the Beckn appointment-booking callbacks.

These produce the ``on_discover`` catalog and the appointment ``on_select`` /
``on_init`` / ``on_confirm`` / ``on_status`` / ``on_cancel`` contract callbacks
that drive the Care scheduling system. The chosen Care ``TokenSlot`` and the
resulting ``TokenBooking`` ride on the contract so the slot survives the
select -> init -> confirm round trip without protocol changes.
"""

import copy

from care.beckn.builders.context import build_callback_context
from care.beckn.constants import (
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_CANCELLED,
    CONTRACT_STATUS_COMPLETE,
    CONTRACT_STATUS_DRAFT,
    DEFAULT_HEALTH_SERVICE_TYPE,
    HEALTH_PARTICIPANT_CONTEXT,
    HEALTH_PERFORMANCE_CONTEXT,
    PARTICIPANT_ROLE_PATIENT,
)
from care.beckn.services.catalog import build_catalogs
from care.beckn.services.identifiers import get_patient_abha_value
from care.emr.resources.patient.spec import GenderChoices

COMPLETED_BOOKING_STATUSES = {"fulfilled", "checked_in", "in_consultation"}
CANCELLED_BOOKING_STATUSES = {"cancelled", "entered_in_error", "rescheduled"}
# Held awaiting a human care-coordinator review (acceptanceMode=MANUAL_REVIEW);
# reported as a DRAFT contract until the review approves it.
PENDING_BOOKING_STATUSES = {"pending", "proposed", "waitlist"}

PATIENT_GENDER_TO_NFH = {
    GenderChoices.male.value: "MALE",
    GenderChoices.female.value: "FEMALE",
    GenderChoices.transgender.value: "OTHER",
    GenderChoices.non_binary.value: "OTHER",
}


def _patient_participant_attributes(patient) -> dict:
    """Build the NFH ``HealthParticipant`` attributes for a Care patient.

    Always carries the required JSON-LD envelope (``@context``/``@type``) so the
    participant validates against the network schema; gender, date of birth and
    ABHA ``healthIds`` are added only when the patient record provides them.
    """
    attributes = {
        "@context": HEALTH_PARTICIPANT_CONTEXT,
        "@type": "hpa:HealthParticipant",
        "participantRole": PARTICIPANT_ROLE_PATIENT,
    }
    nfh_gender = PATIENT_GENDER_TO_NFH.get(patient.gender)
    if nfh_gender:
        attributes["gender"] = nfh_gender
    if patient.date_of_birth:
        attributes["dateOfBirth"] = patient.date_of_birth.isoformat()
    abha_value = get_patient_abha_value(patient)
    if abha_value:
        attributes["healthIds"] = [{"system": "ABHA", "value": abha_value}]
    return attributes


def _inject_patient_health_ids(contract: dict, patient) -> None:
    """Ensure the contract carries a schema-valid PATIENT participant.

    Callbacks may echo an inbound contract whose PATIENT participant is missing
    (or lacks the JSON-LD envelope / ABHA), so the stored patient details are
    merged into the existing participant or, when absent, appended as a fully
    populated one. No-op when the patient is unknown.
    """
    if patient is None:
        return

    attributes = _patient_participant_attributes(patient)
    participants = contract.setdefault("participants", [])
    for participant in participants:
        existing = participant.setdefault("participantAttributes", {})
        if existing.get("participantRole") != PARTICIPANT_ROLE_PATIENT:
            continue
        for key, value in attributes.items():
            if key != "healthIds":
                existing.setdefault(key, value)
        new_health_ids = attributes.get("healthIds", [])
        if new_health_ids:
            health_ids = existing.setdefault("healthIds", [])
            if not any((h.get("system") or "").upper() == "ABHA" for h in health_ids):
                health_ids.extend(new_health_ids)
        return

    participants.append(
        {
            "id": f"participant-patient-{patient.external_id}",
            "descriptor": {"name": patient.name, "shortDesc": "Patient (Subject)"},
            "participantAttributes": attributes,
        }
    )


def _health_service_type(inbound_message: dict) -> str:
    """Read the requested healthServiceType from the inbound contract."""
    contract = (inbound_message or {}).get("contract", {}) or {}
    attributes = contract.get("contractAttributes", {}) or {}
    return attributes.get("healthServiceType") or DEFAULT_HEALTH_SERVICE_TYPE


def build_on_discover(inbound_context: dict) -> dict:
    """Build the ``on_discover`` catalog callback."""
    return {
        "context": build_callback_context(inbound_context, "on_discover"),
        "message": {"catalogs": build_catalogs()},
    }


def _slot_performance(slot, health_service_type: str) -> dict:
    """Represent a bookable ``TokenSlot`` as a Beckn performance entry."""
    return {
        "id": str(slot.external_id),
        "performanceAttributes": {
            "@context": HEALTH_PERFORMANCE_CONTEXT,
            "@type": "hpe:HealthPerformance",
            "healthServiceType": health_service_type,
            "appointmentWindowStart": slot.start_datetime.isoformat(),
            "appointmentWindowEnd": slot.end_datetime.isoformat(),
        },
    }


def build_appt_on_select(inbound_context: dict, inbound_message: dict, slots) -> dict:
    """Echo the selected contract and attach the available slots as performances."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    contract.setdefault("status", {})["code"] = CONTRACT_STATUS_DRAFT
    health_service_type = _health_service_type(inbound_message)
    contract["performance"] = [
        _slot_performance(slot, health_service_type) for slot in slots
    ]
    return {
        "context": build_callback_context(inbound_context, "on_select"),
        "message": message,
    }


def build_appt_on_init(inbound_context: dict, inbound_message: dict, slot) -> dict:
    """Build ``on_init`` for the chosen slot (DRAFT, awaiting confirm)."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    contract.setdefault("status", {})["code"] = CONTRACT_STATUS_DRAFT
    if slot is not None:
        contract["performance"] = [
            _slot_performance(slot, _health_service_type(inbound_message))
        ]
    return {
        "context": build_callback_context(inbound_context, "on_init"),
        "message": message,
    }


def _booking_performance(booking, health_service_type: str) -> dict:
    slot = booking.token_slot
    attributes = {
        "@context": HEALTH_PERFORMANCE_CONTEXT,
        "@type": "hpe:HealthPerformance",
        "healthServiceType": health_service_type,
        "confirmedAppointmentTime": slot.start_datetime.isoformat(),
        "appointmentWindowStart": slot.start_datetime.isoformat(),
        "appointmentWindowEnd": slot.end_datetime.isoformat(),
    }
    return {
        "id": str(slot.external_id),
        "performanceAttributes": attributes,
    }


def _inject_booking(contract: dict, booking, health_service_type: str) -> None:
    """Expose the Care ``TokenBooking`` on the callback contract.

    The booking id is carried in the standard ``contract.id`` and the slot/token
    details in the ``performance`` entry; no custom ``contractAttributes`` keys
    are added because the network ``HealthContract`` schema forbids unknown
    properties (``additionalProperties: false``).
    """
    contract["id"] = str(booking.external_id)
    contract["performance"] = [_booking_performance(booking, health_service_type)]
    _inject_patient_health_ids(contract, getattr(booking, "patient", None))


def _contract_status_for_booking(booking) -> str:
    if booking.status in CANCELLED_BOOKING_STATUSES:
        return CONTRACT_STATUS_CANCELLED
    if booking.status in COMPLETED_BOOKING_STATUSES:
        return CONTRACT_STATUS_COMPLETE
    if booking.status in PENDING_BOOKING_STATUSES:
        return CONTRACT_STATUS_DRAFT
    return CONTRACT_STATUS_ACTIVE


def build_appt_on_confirm(
    inbound_context: dict, inbound_message: dict, booking
) -> dict:
    """Build ``on_confirm`` for the confirmed appointment.

    An auto-accepted booking reports ACTIVE; a booking held for a human
    care-coordinator review (``MANUAL_REVIEW``) is created ``pending`` and
    reported as DRAFT until the review approves it (an unsolicited ``on_status``
    with ACTIVE follows once the coordinator books it in Care).
    """
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    contract.setdefault("status", {})["code"] = _contract_status_for_booking(booking)
    _inject_booking(contract, booking, _health_service_type(inbound_message))
    return {
        "context": build_callback_context(inbound_context, "on_confirm"),
        "message": message,
    }


def build_appt_on_status(inbound_context: dict, inbound_message: dict, booking) -> dict:
    """Build ``on_status`` reflecting the current booking state."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    contract.setdefault("status", {})["code"] = _contract_status_for_booking(booking)
    _inject_booking(contract, booking, _health_service_type(inbound_message))
    return {
        "context": build_callback_context(inbound_context, "on_status"),
        "message": message,
    }


def build_appt_on_update(inbound_context: dict, inbound_message: dict, booking) -> dict:
    """Build ``on_update`` for a rescheduled appointment (ACTIVE, new booking).

    Returned in response to a BAP-initiated ``update`` action; the contract id
    is the replacement booking's id, correlated to the original via the
    unchanged ``transactionId``.
    """
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    contract.setdefault("status", {})["code"] = CONTRACT_STATUS_ACTIVE
    _inject_booking(contract, booking, _health_service_type(inbound_message))
    return {
        "context": build_callback_context(inbound_context, "on_update"),
        "message": message,
    }


def build_appt_on_cancel(inbound_context: dict, inbound_message: dict, booking) -> dict:
    """Build ``on_cancel`` for a cancelled appointment (CANCELLED)."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    contract.setdefault("status", {})["code"] = CONTRACT_STATUS_CANCELLED
    _inject_booking(contract, booking, _health_service_type(inbound_message))
    return {
        "context": build_callback_context(inbound_context, "on_cancel"),
        "message": message,
    }
