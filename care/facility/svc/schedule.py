from datetime import datetime, time

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from care.facility.models.appointment import TokenBooking, TokenSlot
from care.facility.models.patient import PatientRegistration
from care.facility.models.schedule import (
    Availability,
    SchedulableResource,
    ScheduleException,
    SlotType,
    TokenBookingStatus,
)
from care.users.models import User


def get_appointment_slots_for_resource(
    resource,
    from_datetime: datetime,
    to_datetime: datetime,
) -> list[TokenSlot]:
    return get_slots_for_resource(
        resource, from_datetime, to_datetime, [SlotType.APPOINTMENT]
    )


def get_slots_for_resource(
    resource,
    from_datetime: datetime,
    to_datetime: datetime,
    slot_type: list[SlotType] | None = None,
) -> list[TokenSlot]:
    if slot_type is None:
        slot_type = [SlotType.OPEN, SlotType.APPOINTMENT]

    open_availabilities = Availability.objects.filter(
        slot_type__in=slot_type,
        schedule__resource=resource,
        schedule__valid_from__date__lte=to_datetime.date(),
        schedule__valid_to__date__gte=from_datetime.date(),
    )

    closed_exceptions = ScheduleException.objects.filter(
        resource=resource,
        slot_type=SlotType.CLOSED,
        valid_from__lte=to_datetime.date(),
        valid_to__gte=from_datetime.date(),
    )

    open_exceptions = ScheduleException.objects.filter(
        resource=resource,
        slot_type__in=slot_type,
        valid_from__lte=to_datetime.date(),
        valid_to__gte=from_datetime.date(),
    )

    time_slots = []
    created_slots = {
        f"{int(slot.start_datetime.timestamp())}": slot
        for slot in TokenSlot.objects.filter(
            resource=resource,
            start_datetime__date__lte=to_datetime,
            end_datetime__date__gte=from_datetime,
        )
    }

    for availability in open_availabilities:
        # Get slots based on availability schedule
        slot_start = timezone.make_aware(
            datetime.combine(from_datetime.date(), availability.start_time)
        )
        slot_end = timezone.make_aware(
            datetime.combine(to_datetime.date(), time(23, 59, 59))
        )

        while slot_start < slot_end:
            this_slot_end = (
                slot_start
                + timezone.timedelta(minutes=availability.slot_size_in_minutes)
                - timezone.timedelta(seconds=1)
            )

            # Check if current day is in availability's days_of_week
            if slot_start.weekday() not in availability.days_of_week:
                slot_start += timezone.timedelta(days=1)
                continue

            # Check if slot overlaps with any exceptions
            is_closed = check_is_slot_closed(
                closed_exceptions, slot_start, this_slot_end
            )

            if not is_closed:
                slot_id = f"{int(slot_start.timestamp())}"
                if slot_id in created_slots:
                    slot_data = created_slots[slot_id]
                else:
                    slot_data = TokenSlot(
                        resource=resource,
                        start_datetime=slot_start,
                        end_datetime=this_slot_end,
                        tokens_count=availability.tokens_per_slot,
                        tokens_remaining=availability.tokens_per_slot,
                        availability=availability,
                    )
                time_slots.append(slot_data)

            slot_start = this_slot_end + timezone.timedelta(seconds=1)

    for exception in open_exceptions:
        slot_start = datetime.combine(from_datetime.date(), exception.start_time)
        slot_end = datetime.combine(to_datetime.date(), exception.end_time)

        while slot_start < slot_end:
            this_slot_end = (
                slot_start
                + timezone.timedelta(minutes=availability.slot_size_in_minutes)
                - timezone.timedelta(seconds=1)
            )

            slot_id = f"{int(slot_start.timestamp())}"
            if slot_id in created_slots:
                slot_data = created_slots[slot_id]
            else:
                slot_data = TokenSlot(
                    resource=resource,
                    start_datetime=slot_start,
                    end_datetime=this_slot_end,
                    tokens_count=exception.tokens_per_slot,
                    tokens_remaining=exception.tokens_per_slot,
                    availability_exception=exception,
                )

            time_slots.append(slot_data)
            slot_start = this_slot_end + timezone.timedelta(seconds=1)

    return time_slots


def check_is_slot_closed(closed_exceptions, slot_start, this_slot_end):
    for exception in closed_exceptions:
        exception_start = datetime.combine(slot_start.date(), exception.start_time)
        exception_end = datetime.combine(slot_start.date(), exception.end_time)
        if slot_start < exception_end and this_slot_end > exception_start:
            is_closed = True
            break
    return is_closed


@transaction.atomic
def book_slot(
    booked_by: User,
    patient: PatientRegistration,
    resource: SchedulableResource,
    slot_type: SlotType,
    slot_start: datetime,
    reason_for_visit: str | None = None,
) -> None:
    search_range = (
        slot_start,
        slot_start + timezone.timedelta(hours=12),
    )
    slots = get_slots_for_resource(
        resource,
        search_range[0],
        search_range[1],
        [slot_type],
    )
    try:
        slot = next(
            s for s in slots if s.start_datetime.timestamp() == slot_start.timestamp()
        )
    except StopIteration as e:
        msg = "Slot not found"
        raise ValueError(msg) from e

    if not slot.pk:
        slot.save()

    booking = TokenBooking.objects.create(
        token_slot=slot,
        patient=patient,
        status=TokenBookingStatus.REQUESTED,
        booked_by=booked_by,
        reason_for_visit=reason_for_visit,
    )
    TokenSlot.objects.filter(id=slot.id).update(
        tokens_remaining=F("tokens_remaining") - 1
    )
    return booking
