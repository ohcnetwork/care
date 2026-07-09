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
    HEALTH_PERFORMANCE_CONTEXT,
    PARTICIPANT_ROLE_PATIENT,
)
from care.beckn.services.catalog import build_catalogs
from care.beckn.services.identifiers import get_patient_abha_value

# Care TokenBooking.status values that map to a completed appointment.
COMPLETED_BOOKING_STATUSES = {"fulfilled", "checked_in", "in_consultation"}
CANCELLED_BOOKING_STATUSES = {"cancelled", "entered_in_error", "rescheduled"}


def _inject_patient_health_ids(contract: dict, patient) -> None:
    """Ensure the contract's PATIENT participant carries the ABHA ``healthIds``.

    Status/retrieve callbacks may echo an inbound contract without the patient's
    ABHA, so the stored identifier is merged into (or added as) the PATIENT
    participant. No-op when the patient has no ABHA identifier.
    """
    abha_value = get_patient_abha_value(patient)
    if not abha_value:
        return

    abha_entry = {"system": "ABHA", "value": abha_value}
    participants = contract.setdefault("participants", [])
    for participant in participants:
        attributes = participant.setdefault("participantAttributes", {})
        if attributes.get("participantRole") == PARTICIPANT_ROLE_PATIENT:
            health_ids = attributes.setdefault("healthIds", [])
            if not any((h.get("system") or "").upper() == "ABHA" for h in health_ids):
                health_ids.append(abha_entry)
            return

    participants.append(
        {
            "id": f"participant-patient-{patient.external_id}",
            "descriptor": {"name": patient.name},
            "participantAttributes": {
                "participantRole": PARTICIPANT_ROLE_PATIENT,
                "healthIds": [abha_entry],
            },
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
    return CONTRACT_STATUS_ACTIVE


def build_appt_on_confirm(
    inbound_context: dict, inbound_message: dict, booking
) -> dict:
    """Build ``on_confirm`` for a booked appointment (ACTIVE, contract.id=booking)."""
    message = copy.deepcopy(inbound_message or {})
    contract = message.setdefault("contract", {})
    contract.setdefault("status", {})["code"] = CONTRACT_STATUS_ACTIVE
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
