"""Wrappers over the Care scheduling system for the Beckn appointment flow.

These reuse the existing scheduling primitives (slot generation, booking
creation/cancellation, token generation) so the Beckn webhook can drive the same
behaviour as the HTTP scheduling API without going through DRF.
"""

import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from care.emr.api.viewsets.scheduling.availability import (
    convert_availability_and_exceptions_to_slots,
    lock_create_appointment,
)
from care.emr.api.viewsets.scheduling.booking import TokenBookingViewSet
from care.emr.models.scheduling.booking import TokenBooking, TokenSlot
from care.emr.models.scheduling.schedule import Availability, AvailabilityException
from care.emr.resources.scheduling.schedule.spec import SlotTypeOptions


def list_slots_for_day(resource, day: datetime.date, *, public_only: bool = True):
    """Return the bookable ``TokenSlot``s for a resource on a given day.

    Mirrors ``SlotViewSet.get_slots_for_day_handler`` but operates on a
    ``SchedulableResource`` directly and returns model instances (creating any
    missing future slots) instead of an HTTP response.
    """
    availabilities = Availability.objects.filter(
        slot_type=SlotTypeOptions.appointment.value,
        schedule__valid_from__lte=day,
        schedule__valid_to__gte=day,
        schedule__resource=resource,
    )
    if public_only:
        availabilities = availabilities.filter(schedule__is_public=True)

    calculated_dow_availabilities = []
    for schedule_availability in availabilities:
        for day_availability in schedule_availability.availability:
            if day_availability["day_of_week"] == day.weekday():
                calculated_dow_availabilities.append(
                    {
                        "availability": day_availability,
                        "slot_size_in_minutes": schedule_availability.slot_size_in_minutes,
                        "availability_id": schedule_availability.id,
                    }
                )

    exceptions = AvailabilityException.objects.filter(
        resource=resource,
        valid_from__lte=day,
        valid_to__gte=day,
    )
    candidate_slots = convert_availability_and_exceptions_to_slots(
        calculated_dow_availabilities, exceptions, day
    )

    existing = TokenSlot.objects.filter(
        start_datetime__date=day,
        end_datetime__date=day,
        resource=resource,
    )
    if public_only:
        existing = existing.filter(availability__schedule__is_public=True)
    for slot in existing:
        slot_key = (
            f"{slot.availability.id}-"
            f"{timezone.make_naive(slot.start_datetime).time()}-"
            f"{timezone.make_naive(slot.end_datetime).time()}"
        )
        if (
            slot_key in candidate_slots
            and candidate_slots[slot_key]["availability_id"] == slot.availability.id
        ):
            candidate_slots.pop(slot_key)

    for slot in candidate_slots.values():
        end_datetime = datetime.datetime.combine(day, slot["end_time"], tzinfo=None)
        if end_datetime < timezone.make_naive(timezone.now()):
            continue
        TokenSlot.objects.create(
            resource=resource,
            start_datetime=datetime.datetime.combine(
                day, slot["start_time"], tzinfo=None
            ),
            end_datetime=end_datetime,
            availability_id=slot["availability_id"],
        )

    slots = TokenSlot.objects.filter(
        start_datetime__date=day,
        end_datetime__date=day,
        resource=resource,
    ).select_related("availability", "availability__schedule")
    if public_only:
        slots = slots.filter(availability__schedule__is_public=True)
    # Only offer slots that are still bookable; a slot whose end has passed can
    # never be booked, so exclude it from on_select so the BAP only sees
    # actionable options. Past dates and finished time windows are excluded by
    # the end_datetime filter.
    slots = slots.filter(end_datetime__gt=timezone.now())
    # Exclude fully-booked slots: a slot is full once its allocations reach the
    # availability capacity (tokens_per_slot), matching lock_create_appointment.
    slots = slots.filter(allocated__lt=F("availability__tokens_per_slot"))
    return list(slots.order_by("start_datetime"))


def resolve_token_slot(slot_id=None, resource=None, start_datetime=None):
    """Resolve a ``TokenSlot`` by external id, falling back to resource + time."""
    if slot_id:
        slot = TokenSlot.objects.filter(external_id=slot_id).first()
        if slot:
            return slot
    if resource is not None and start_datetime is not None:
        return TokenSlot.objects.filter(
            resource=resource, start_datetime=start_datetime
        ).first()
    return None


def book_appointment(token_slot, patient, user, note=""):
    """Book an appointment for ``patient`` in ``token_slot`` and return it."""
    return lock_create_appointment(token_slot, patient, user, note or "")


def cancel_appointment(booking, user, reason="cancelled", note=None):
    """Cancel a ``TokenBooking`` and return the updated instance."""
    return TokenBookingViewSet.cancel_appointment_handler(
        booking, {"reason": reason, "note": note}, user
    )


def reschedule_appointment(booking, new_slot, user, note=""):
    """Reschedule ``booking`` to ``new_slot`` and return the replacement booking.

    Mirrors the Care reschedule action without going through DRF: the original
    booking is cancelled with reason ``rescheduled`` and a new booking is created
    for the chosen slot.
    """
    from care.emr.resources.scheduling.slot.spec import BookingStatusChoices

    with transaction.atomic():
        TokenBookingViewSet.cancel_appointment_handler(
            booking,
            {
                "reason": BookingStatusChoices.rescheduled.value,
                "note": note or booking.note,
            },
            user,
        )
        return lock_create_appointment(new_slot, booking.patient, user, note or "")


def find_booking(external_id):
    """Return a ``TokenBooking`` by external id (the Beckn contract id)."""
    if not external_id:
        return None
    return (
        TokenBooking.objects.filter(external_id=external_id)
        .select_related(
            "token_slot",
            "token_slot__resource",
            "token_slot__resource__facility",
            "patient",
        )
        .first()
    )


def ensure_token(booking, user):
    """Best-effort: generate a queue ``Token`` for a confirmed booking.

    Returns the token (existing or newly created) or ``None`` when the facility
    has no token category configured for the resource. Never raises so confirm
    delivery is unaffected by token-generation gaps.
    """
    from care.emr.models.scheduling.token import (
        Token,
        TokenCategory,
        TokenQueue,
    )
    from care.emr.resources.scheduling.token.spec import TokenStatusOptions
    from care.utils.lock import Lock

    if booking.token:
        return booking.token

    resource = booking.token_slot.resource
    facility = resource.facility
    category = TokenCategory.objects.filter(
        facility=facility, resource_type=resource.resource_type
    ).first()
    if not category:
        return None

    token_date = timezone.make_naive(
        booking.token_slot.start_datetime + datetime.timedelta(seconds=1)
    ).date()
    filters = {"facility": facility, "resource": resource, "date": token_date}
    queue_exists = TokenQueue.objects.filter(**filters).exists()
    filters["system_generated"] = True
    queue = TokenQueue.objects.filter(**filters).first()
    if not queue:
        filters["name"] = "System Generated"
        if not queue_exists:
            filters["is_primary"] = True
        queue = TokenQueue.objects.create(**filters)

    with Lock(f"booking:token:{queue.id}"), transaction.atomic():
        number = Token.objects.filter(queue=queue, category=category).count() + 1
        token = Token.objects.create(
            facility=facility,
            queue=queue,
            category=category,
            number=number,
            status=TokenStatusOptions.CREATED.value,
            booking=booking,
            patient=booking.patient,
        )
        booking.token = token
        booking.save(update_fields=["token", "modified_date"])
    return token
