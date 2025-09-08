import datetime
from datetime import time, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from pydantic import UUID4, BaseModel, model_validator
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRRetrieveMixin
from care.emr.api.viewsets.scheduling.schedule import get_or_create_resource
from care.emr.models import AvailabilityException, Schedule, TokenBooking
from care.emr.models.patient import Patient
from care.emr.models.scheduling.booking import TokenSlot
from care.emr.models.scheduling.schedule import Availability
from care.emr.resources.charge_item.apply_charge_item_definition import (
    apply_charge_item_definition,
)
from care.emr.resources.charge_item.spec import ChargeItemResourceOptions
from care.emr.resources.scheduling.schedule.spec import (
    SchedulableResourceTypeOptions,
    SlotTypeOptions,
)
from care.emr.resources.scheduling.slot.spec import (
    CANCELLED_STATUS_CHOICES,
    COMPLETED_STATUS_CHOICES,
    TokenBookingReadSpec,
    TokenSlotBaseSpec,
)
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.base import SingleFacilityTagManager
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController
from care.utils.lock import Lock
from care.utils.time_util import care_now


class SlotsForDayRequestSpec(BaseModel):
    resource_type: SchedulableResourceTypeOptions
    resource_id: UUID4
    day: datetime.date


class AppointmentBookingSpec(BaseModel):
    patient: UUID4
    note: str

    tags: list[UUID4] = []


class AvailabilityStatsRequestSpec(BaseModel):
    from_date: datetime.date
    to_date: datetime.date
    resource_type: SchedulableResourceTypeOptions
    resource_id: UUID4

    @model_validator(mode="after")
    def validate_period(self):
        max_period = 32
        if self.from_date > self.to_date:
            raise ValidationError("From Date cannot be after To Date")
        if self.to_date - self.from_date > datetime.timedelta(days=max_period):
            msg = f"Period cannot be be greater than {max_period} days"
            raise ValidationError(msg)


def convert_availability_and_exceptions_to_slots(availabilities, exceptions, day):
    slots = {}
    for availability in availabilities:
        start_time = datetime.datetime.combine(
            day,
            time.fromisoformat(availability["availability"]["start_time"]),
            tzinfo=None,
        )
        end_time = datetime.datetime.combine(
            day,
            time.fromisoformat(availability["availability"]["end_time"]),
            tzinfo=None,
        )
        slot_size_in_minutes = availability["slot_size_in_minutes"]
        availability_id = availability["availability_id"]
        current_time = start_time
        i = 0
        while current_time < end_time:
            i += 1
            if i == settings.MAX_SLOTS_PER_AVAILABILITY + 1:
                # Failsafe to prevent infinite loop
                break

            conflicting = False
            for exception in exceptions:
                exception_start_time = datetime.datetime.combine(
                    day, exception.start_time, tzinfo=None
                )
                exception_end_time = datetime.datetime.combine(
                    day, exception.end_time, tzinfo=None
                )
                if (
                    exception_start_time
                    < (current_time + datetime.timedelta(minutes=slot_size_in_minutes))
                ) and exception_end_time > current_time:
                    conflicting = True

            if not conflicting:
                slots[
                    f"{current_time.time()}-{(current_time + datetime.timedelta(minutes=slot_size_in_minutes)).time()}"
                ] = {
                    "start_time": current_time.time(),
                    "end_time": (
                        current_time + datetime.timedelta(minutes=slot_size_in_minutes)
                    ).time(),
                    "availability_id": availability_id,
                }

            current_time += datetime.timedelta(minutes=slot_size_in_minutes)
    return slots


def lock_create_appointment(token_slot, patient, created_by, note):
    with Lock(f"booking:resource:{token_slot.resource.id}"), transaction.atomic():
        if token_slot.end_datetime < timezone.now():
            raise ValidationError("Slot is already past")
        if token_slot.allocated >= token_slot.availability.tokens_per_slot:
            raise ValidationError("Slot is already full")
        if (
            TokenBooking.objects.filter(token_slot=token_slot, patient=patient)
            .exclude(status__in=COMPLETED_STATUS_CHOICES)
            .exists()
        ):
            raise ValidationError("Patient already has a booking for this slot")
        token_slot.allocated += 1
        token_slot.save()
        booking = TokenBooking.objects.create(
            token_slot=token_slot,
            patient=patient,
            booked_by=created_by,
            created_by=created_by,
            updated_by=created_by,
            note=note,
            status="booked",
        )
        # Generate Charge Item
        schedule = booking.token_slot.availability.schedule
        last_booking = (
            TokenBooking.objects.exclude(status__in=CANCELLED_STATUS_CHOICES)
            .filter(
                patient=patient,
                token_slot__availability__schedule=schedule,
                charge_item__isnull=False,
                token_slot__start_datetime__lte=token_slot.start_datetime,
            )
            .order_by("-token_slot__start_datetime")
        ).first()
        if last_booking:
            booking_start_time = last_booking.token_slot.start_datetime
            current_time = timezone.now()
            diff_days = (booking_start_time - current_time).days
        else:
            diff_days = -1
        if (
            schedule.revisit_allowed_days
            and diff_days != -1
            and diff_days <= schedule.revisit_allowed_days
        ):
            charge_item_definition = schedule.revisit_charge_item_definition
        else:
            charge_item_definition = schedule.charge_item_definition
        if charge_item_definition:
            charge_item = apply_charge_item_definition(
                charge_item_definition,
                patient,
                token_slot.resource.facility,
                quantity=1,
            )
            charge_item.service_resource = ChargeItemResourceOptions.appointment.value
            charge_item.service_resource_id = str(booking.external_id)
            charge_item.save()
            booking.charge_item = charge_item
            booking.save(update_fields=["charge_item"])
        return booking


class SlotViewSet(EMRRetrieveMixin, EMRBaseViewSet):
    database_model = TokenSlot
    pydantic_read_model = TokenSlotBaseSpec

    @action(detail=False, methods=["POST"])
    def get_slots_for_day(self, request, *args, **kwargs):
        # TODO : Add Authorization, Need to confirm what works here
        return self.get_slots_for_day_handler(
            self.kwargs["facility_external_id"], request.data
        )

    @classmethod
    def get_slots_for_day_handler(cls, facility_external_id, request_data):
        request_data = SlotsForDayRequestSpec(**request_data)
        facility = get_object_or_404(Facility, external_id=facility_external_id)
        resource = get_or_create_resource(
            request_data.resource_type,
            request_data.resource_id,
            facility,
        )
        if not resource:
            raise ValidationError("Resource is not schedulable")
        # Find all relevant schedules
        availabilities = Availability.objects.filter(
            slot_type=SlotTypeOptions.appointment.value,
            schedule__valid_from__lte=request_data.day,
            schedule__valid_to__gte=request_data.day,
            schedule__resource=resource,
        )
        # Fetch all availabilities for that day of week
        calculated_dow_availabilities = []
        for schedule_availability in availabilities:
            for day_availability in schedule_availability.availability:
                if day_availability["day_of_week"] == request_data.day.weekday():
                    calculated_dow_availabilities.append(
                        {
                            "availability": day_availability,
                            "slot_size_in_minutes": schedule_availability.slot_size_in_minutes,
                            "availability_id": schedule_availability.id,
                        }
                    )
        exceptions = AvailabilityException.objects.filter(
            resource=resource,
            valid_from__lte=request_data.day,
            valid_to__gte=request_data.day,
        )
        # Generate all slots already created for that day, exclude anything that conflicts with availability exception
        slots = convert_availability_and_exceptions_to_slots(
            calculated_dow_availabilities, exceptions, request_data.day
        )
        # Fetch all existing slots in that day
        created_slots = TokenSlot.objects.filter(
            start_datetime__date=request_data.day,
            end_datetime__date=request_data.day,
            resource=resource,
        )
        for slot in created_slots:
            slot_key = f"{timezone.make_naive(slot.start_datetime).time()}-{timezone.make_naive(slot.end_datetime).time()}"
            if (
                slot_key in slots
                and slots[slot_key]["availability_id"] == slot.availability.id
            ):
                slots.pop(slot_key)

        # Create everything else
        for _, slot in slots.items():
            end_datetime = datetime.datetime.combine(
                request_data.day, slot["end_time"], tzinfo=None
            )
            # Skip creating slots in the past
            if end_datetime < timezone.make_naive(timezone.now()):
                continue
            TokenSlot.objects.create(
                resource=resource,
                start_datetime=datetime.datetime.combine(
                    request_data.day, slot["start_time"], tzinfo=None
                ),
                end_datetime=end_datetime,
                availability_id=slot["availability_id"],
            )
        # Compare and figure out what needs to be created
        return Response(
            {
                "results": [
                    TokenSlotBaseSpec.serialize(slot).model_dump(exclude=["meta"])
                    for slot in TokenSlot.objects.filter(
                        start_datetime__date=request_data.day,
                        end_datetime__date=request_data.day,
                        resource=resource,
                    ).select_related("availability")
                ]
            }
        )
        # Find all existing Slot objects for that period
        # Get list of all slots, create if missed
        # Return slots

    @classmethod
    def create_appointment_handler(cls, obj, request_data, user):
        request_data = AppointmentBookingSpec(**request_data)
        patient = Patient.objects.filter(external_id=request_data.patient).first()
        with transaction.atomic():
            if (
                TokenBooking.objects.filter(
                    patient=patient,
                    token_slot__start_datetime__gte=care_now(),
                )
                .exclude(status__in=COMPLETED_STATUS_CHOICES)
                .count()
                >= settings.MAX_APPOINTMENTS_PER_PATIENT
            ):
                error = f"Patient already has maximum number of appointments ({settings.MAX_APPOINTMENTS_PER_PATIENT})"
                raise ValidationError(error)

            if not patient:
                raise ValidationError("Patient not found")
            appointment = lock_create_appointment(obj, patient, user, request_data.note)
            if request_data.tags:
                tag_manager = SingleFacilityTagManager()
                tag_manager.set_tags(
                    TagResource.token_booking,
                    appointment,
                    request_data.tags,
                    user,
                    obj.resource.facility,
                )
        return Response(
            TokenBookingReadSpec.serialize(appointment).model_dump(exclude=["meta"])
        )

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_create_booking", model_instance.resource, self.request.user
        ):
            raise PermissionDenied("You do not have permission to create appointments")

    @action(detail=True, methods=["POST"])
    def create_appointment(self, request, *args, **kwargs):
        slot_obj = self.get_object()
        self.authorize_update(None, slot_obj)
        return self.create_appointment_handler(slot_obj, request.data, request.user)

    @action(detail=False, methods=["POST"])
    def availability_stats(self, request, *args, **kwargs):
        """
        Return the stats for available slots compared to the booked slots
        ie Availability percentage.
        """
        request_data = AvailabilityStatsRequestSpec(**request.data)
        # Fetch the entire schedule and calculate total slots available for each day
        facility = get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )
        resource = get_or_create_resource(
            request_data.resource_type,
            request_data.resource_id,
            facility,
        )
        if not resource:
            raise ValidationError("Resource is not schedulable")

        self.authorize_resource_read(resource)

        schedules = Schedule.objects.filter(
            valid_from__lte=request_data.to_date,
            valid_to__gte=request_data.from_date,
            resource=resource,
        ).values()

        # Cache availabilities
        availabilities = {}
        for schedule in schedules:
            availabilities[schedule["id"]] = Availability.objects.filter(
                schedule_id=schedule["id"],
                slot_type=SlotTypeOptions.appointment.value,
            ).values()

        availability_exceptions = AvailabilityException.objects.filter(
            valid_from__lte=request_data.to_date,
            valid_to__gte=request_data.from_date,
            resource=resource,
        ).values()

        # Generate a list of all available days as a dict

        days = {}
        response_days = {}
        day = request_data.from_date
        while day <= request_data.to_date:
            days[day] = {"total_slots": 0, "booked_slots": 0}
            response_days[str(day)] = {"total_slots": 0, "booked_slots": 0}
            day += timedelta(days=1)

        for day, day_data in days.items():
            # Calculate all matching schedules
            current_schedules = []
            for schedule in schedules:
                valid_from = timezone.make_naive(schedule["valid_from"]).date()
                valid_to = timezone.make_naive(schedule["valid_to"]).date()
                if valid_from <= day <= valid_to:
                    current_schedules.append(schedule)
            # Calculate availability exception for that day
            exceptions = []
            for exception in availability_exceptions:
                valid_from = exception["valid_from"]
                valid_to = exception["valid_to"]
                if valid_from <= day <= valid_to:
                    exceptions.append(exception)
            # Calculate slots based on these data

            slots_count = calculate_slots(
                day, availabilities, current_schedules, exceptions
            )
            day_data["total_slots"] = slots_count
            response_days[str(day)]["total_slots"] = slots_count
        # Query slots data for these dates, group by date and sum up count

        booked_slots = (
            TokenSlot.objects.filter(
                start_datetime__date__lte=request_data.to_date,
                end_datetime__date__gt=request_data.from_date,
                resource=resource,
            )
            .values("start_datetime__date")
            .annotate(allocated_sum=Sum("allocated"))
            .values("allocated_sum", "start_datetime__date")
        )

        for slot in booked_slots:
            response_days[str(slot["start_datetime__date"])]["booked_slots"] = slot[
                "allocated_sum"
            ]
        # Query all the booked slots for the given days and get the total booked

        return Response(response_days)

    def authorize_retrieve(self, model_instance):
        self.authorize_resource_read(model_instance.resource)

    def authorize_resource_read(self, resource_obj):
        if not AuthorizationController.call(
            "can_list_booking", resource_obj, self.request.user
        ):
            raise PermissionDenied("You do not have permission to list bookings")

    def get_queryset(self):
        return super().get_queryset().select_related("resource")


def calculate_slots(
    date: datetime.date,
    availabilities: list[Availability],
    schedules,
    exceptions: list[AvailabilityException],
):
    # We don't care about duplicate slots because they won't exist because of our validations
    day_of_week = date.weekday()
    slots = 0
    for schedule in schedules:
        for availability in availabilities[schedule["id"]]:
            for available_slot in availability["availability"]:
                if available_slot["day_of_week"] != day_of_week:
                    continue
                start_time = datetime.datetime.combine(
                    date, time.fromisoformat(available_slot["start_time"]), tzinfo=None
                )
                end_time = datetime.datetime.combine(
                    date, time.fromisoformat(available_slot["end_time"]), tzinfo=None
                )
                current_start_time = start_time
                while current_start_time < end_time:
                    conflicting = False
                    current_end_time = current_start_time + timedelta(
                        minutes=availability["slot_size_in_minutes"]
                    )
                    for exception in exceptions:
                        exception_start_time = datetime.datetime.combine(
                            date, exception["start_time"], tzinfo=None
                        )
                        exception_end_time = datetime.datetime.combine(
                            date, exception["end_time"], tzinfo=None
                        )
                        if (
                            exception_start_time < current_end_time
                            and exception_end_time > current_start_time
                        ):
                            conflicting = True
                    current_start_time = current_end_time
                    if conflicting:
                        continue
                    slots += availability["tokens_per_slot"]
    return slots
