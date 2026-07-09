"""Per-action handlers for the BPP webhook.

Each handler receives the inbound Beckn ``context`` and ``message`` and returns
the corresponding ``on_*`` callback payload. The ``select``/``init``/
``confirm``/``status``/``cancel`` actions are shared between two flows and are
routed by :func:`care.beckn.mappers.resolve_flow`:

* the **referral** flow (T1/T2) creates/approves a Care ``ResourceRequest``;
* the **appointment** flow drives the Care scheduling system
  (``TokenSlot``/``TokenBooking``).

``discover`` is always served by the appointment flow (catalog publish).
"""

import datetime

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError as DRFValidationError

from care.beckn.builders.catalog import (
    build_appt_on_cancel,
    build_appt_on_confirm,
    build_appt_on_init,
    build_appt_on_select,
    build_appt_on_status,
    build_appt_on_update,
    build_on_discover,
)
from care.beckn.builders.referral import (
    build_on_confirm,
    build_on_init,
    build_on_select,
    build_on_status,
)
from care.beckn.config import resolve_origin_facility
from care.beckn.constants import FLOW_APPOINTMENT
from care.beckn.mappers import (
    extract_health_ids,
    find_patient_participant,
    get_confirmed_appointment_time,
    get_contract,
    get_contract_attributes,
    get_requested_date,
    get_selected_resource_id,
    get_selected_slot_id,
    resolve_flow,
)
from care.beckn.services import scheduling
from care.beckn.services.identifiers import attach_abha_identifier
from care.beckn.services.lookup import find_resource_request
from care.beckn.services.patient import find_or_create_patient
from care.emr.models.resource_request import ResourceRequest
from care.emr.models.scheduling import SchedulableResource
from care.emr.resources.resource_request.spec import CategoryChoices, StatusChoices

# NFH clinicalUrgencyTier -> ResourceRequest priority (higher = more urgent).
URGENCY_PRIORITY = {
    "EMERGENCY": 3,
    "URGENT": 2,
    "ROUTINE": 1,
}


class BecknActionError(Exception):
    """Raised when an inbound action cannot be processed."""


def _first_validation_message(exc: DRFValidationError) -> str:
    """Return a readable message from a DRF ``ValidationError``."""
    detail = getattr(exc, "detail", None)
    if isinstance(detail, list) and detail:
        return str(detail[0])
    if isinstance(detail, dict) and detail:
        first = next(iter(detail.values()))
        if isinstance(first, list) and first:
            return str(first[0])
        return str(first)
    return str(detail or exc)


def _resolve_system_user():
    from django.conf import settings

    from care.users.models import User

    username = getattr(settings, "BECKN_SYSTEM_USERNAME", None)
    if username:
        return User.objects.filter(username=username).first()
    return None


# ---------------------------------------------------------------------------
# Referral flow (T1/T2) — unchanged behaviour, routed when resolve_flow == referral
# ---------------------------------------------------------------------------


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


def _referral_select(context: dict, message: dict) -> dict:
    """Echo the selected offer (no state change)."""
    return build_on_select(context, message)


def _referral_init(context: dict, message: dict) -> dict:
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


def _referral_confirm(context: dict, message: dict) -> dict:
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

        # ABHA may be carried on the confirm; record it idempotently.
        if resource_request.related_patient_id:
            participant = find_patient_participant(message)
            attach_abha_identifier(
                resource_request.related_patient, extract_health_ids(participant)
            )

    return build_on_confirm(context, message, resource_request)


def _referral_status(context: dict, message: dict) -> dict:
    """Return the current referral state as on_status."""
    resource_request = find_resource_request(context, message)
    if resource_request is None:
        raise BecknActionError("Referral not found for status")
    return build_on_status(context, message, resource_request)


# ---------------------------------------------------------------------------
# Appointment flow — drives the Care scheduling system
# ---------------------------------------------------------------------------


def _parse_day(value: str | None) -> datetime.date:
    """Parse an ISO date/date-time into a date, defaulting to today."""
    if value:
        parsed_date = parse_date(value[:10])
        if parsed_date:
            return parsed_date
        parsed_dt = parse_datetime(value)
        if parsed_dt:
            return parsed_dt.date()
    return timezone.localdate()


def _resolve_schedulable_resource(message: dict):
    resource_id = get_selected_resource_id(message)
    if not resource_id:
        return None
    return (
        SchedulableResource.objects.select_related("facility")
        .filter(external_id=resource_id)
        .first()
    )


def _appointment_discover(context: dict, message: dict) -> dict:
    """Publish the catalog of bookable resources as on_discover."""
    return build_on_discover(context)


def _appointment_select(context: dict, message: dict) -> dict:
    """Return concrete bookable slots for the selected resource as on_select."""
    resource = _resolve_schedulable_resource(message)
    if resource is None:
        raise BecknActionError(
            "No Care schedulable resource matched the selected resource id"
        )
    day = _parse_day(get_requested_date(context, message))
    slots = scheduling.list_slots_for_day(resource, day)
    return build_appt_on_select(context, message, slots)


def _resolve_chosen_slot(message: dict):
    slot_id = get_selected_slot_id(message)
    slot = scheduling.resolve_token_slot(slot_id=slot_id)
    if slot is not None:
        return slot
    confirmed_time = get_confirmed_appointment_time(message)
    resource = _resolve_schedulable_resource(message)
    if confirmed_time and resource is not None:
        start = parse_datetime(confirmed_time)
        if start is not None:
            return scheduling.resolve_token_slot(
                resource=resource, start_datetime=start
            )
    return None


def _appointment_init(context: dict, message: dict) -> dict:
    """Resolve the patient and the chosen slot, return on_init (no booking yet)."""
    slot = _resolve_chosen_slot(message)
    if slot is None:
        raise BecknActionError("No Care slot matched the chosen appointment")
    facility = slot.resource.facility
    user = _resolve_system_user()
    participant = find_patient_participant(message)
    find_or_create_patient(message, participant, facility, user)
    return build_appt_on_init(context, message, slot)


def _appointment_confirm(context: dict, message: dict) -> dict:
    """Book the chosen slot, generate a token, return on_confirm."""
    slot = _resolve_chosen_slot(message)
    if slot is None:
        raise BecknActionError("No Care slot matched the chosen appointment")
    facility = slot.resource.facility
    user = _resolve_system_user()
    participant = find_patient_participant(message)
    patient = find_or_create_patient(message, participant, facility, user)
    if patient is None:
        raise BecknActionError("No patient participant found to book the appointment")

    try:
        with transaction.atomic():
            booking = scheduling.book_appointment(slot, patient, user)
            scheduling.ensure_token(booking, user)
            beckn = booking.meta.setdefault("beckn", {})
            beckn["transactionId"] = (context or {}).get("transactionId")
            beckn["bapId"] = (context or {}).get("bapId")
            beckn["bapUri"] = (context or {}).get("bapUri")
            # Persist the full inbound context and message snapshot so that
            # unsolicited on_status callbacks can be rebuilt and routed back to
            # the BAP when the booking changes, without the BAP calling status.
            beckn["context"] = context or {}
            beckn["message"] = message or {}
            booking.save(update_fields=["meta", "modified_date"])
    except DRFValidationError as exc:
        # Surface the booking rule (slot past/full/duplicate) as a clean NACK.
        raise BecknActionError(_first_validation_message(exc)) from exc

    booking.refresh_from_db()
    return build_appt_on_confirm(context, message, booking)


def _appointment_status(context: dict, message: dict) -> dict:
    """Return the current appointment state as on_status."""
    booking = scheduling.find_booking(get_contract(message).get("id"))
    if booking is None:
        raise BecknActionError("Appointment not found for status")
    return build_appt_on_status(context, message, booking)


def _appointment_cancel(context: dict, message: dict) -> dict:
    """Cancel the appointment and return on_cancel."""
    booking = scheduling.find_booking(get_contract(message).get("id"))
    if booking is None:
        raise BecknActionError("Appointment not found for cancel")
    user = _resolve_system_user()
    attributes = get_contract_attributes(message)
    note = attributes.get("cancellationReason")
    booking = scheduling.cancel_appointment(booking, user, note=note)
    return build_appt_on_cancel(context, message, booking)


def _appointment_update(context: dict, message: dict) -> dict:
    """Reschedule the appointment to the chosen new slot and return on_update.

    The replacement booking inherits the original's Beckn context (so future
    Care-side changes still notify the BAP). The unsolicited on_status callbacks
    are suppressed for this BAP-initiated change: the BAP gets a single
    on_update carrying the new booking's contract id, correlated to the original
    via the unchanged transactionId.
    """
    booking = scheduling.find_booking(get_contract(message).get("id"))
    if booking is None:
        raise BecknActionError("Appointment not found for update")
    new_slot = _resolve_chosen_slot(message)
    if new_slot is None:
        raise BecknActionError("No Care slot matched the requested new appointment")
    if new_slot.id == booking.token_slot_id:
        raise BecknActionError("Cannot reschedule to the same slot")
    user = _resolve_system_user()

    from care.beckn.signals import suppress_beckn_notifications
    from care.beckn.tasks import carry_beckn_context

    try:
        with suppress_beckn_notifications(), transaction.atomic():
            new_booking = scheduling.reschedule_appointment(booking, new_slot, user)
            carry_beckn_context(booking, new_booking)
    except DRFValidationError as exc:
        raise BecknActionError(_first_validation_message(exc)) from exc

    new_booking.refresh_from_db()
    return build_appt_on_update(context, message, new_booking)


# ---------------------------------------------------------------------------
# Public action handlers — route shared actions to the resolved flow
# ---------------------------------------------------------------------------


def handle_discover(context: dict, message: dict) -> dict:
    return _appointment_discover(context, message)


def handle_select(context: dict, message: dict) -> dict:
    if resolve_flow("select", context, message) == FLOW_APPOINTMENT:
        return _appointment_select(context, message)
    return _referral_select(context, message)


def handle_init(context: dict, message: dict) -> dict:
    if resolve_flow("init", context, message) == FLOW_APPOINTMENT:
        return _appointment_init(context, message)
    return _referral_init(context, message)


def handle_confirm(context: dict, message: dict) -> dict:
    if resolve_flow("confirm", context, message) == FLOW_APPOINTMENT:
        return _appointment_confirm(context, message)
    return _referral_confirm(context, message)


def handle_status(context: dict, message: dict) -> dict:
    if resolve_flow("status", context, message) == FLOW_APPOINTMENT:
        return _appointment_status(context, message)
    return _referral_status(context, message)


def handle_cancel(context: dict, message: dict) -> dict:
    if resolve_flow("cancel", context, message) == FLOW_APPOINTMENT:
        return _appointment_cancel(context, message)
    raise BecknActionError("Cancel is not supported for the referral flow")


def handle_update(context: dict, message: dict) -> dict:
    if resolve_flow("update", context, message) == FLOW_APPOINTMENT:
        return _appointment_update(context, message)
    raise BecknActionError("Update is not supported for the referral flow")


ACTION_HANDLERS = {
    "discover": handle_discover,
    "select": handle_select,
    "init": handle_init,
    "confirm": handle_confirm,
    "status": handle_status,
    "update": handle_update,
    "cancel": handle_cancel,
}
