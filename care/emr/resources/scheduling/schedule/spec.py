import datetime
from datetime import UTC
from enum import Enum

from django.conf import settings
from django.db.models import Sum
from pydantic import UUID4, Field, field_validator, model_validator
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404

from care.emr.models.scheduling.booking import TokenSlot
from care.emr.models.scheduling.schedule import (
    Availability,
    SchedulableUserResource,
    Schedule,
)
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec
from care.facility.models import Facility
from care.users.models import User
from care.utils.time_util import care_now


class SlotTypeOptions(str, Enum):
    open = "open"
    appointment = "appointment"
    closed = "closed"


class AvailabilityDateTimeSpec(EMRResource):
    day_of_week: int = Field(le=6)
    start_time: datetime.time
    end_time: datetime.time


class AvailabilityBaseSpec(EMRResource):
    __model__ = Availability
    __exclude__ = ["schedule"]

    id: UUID4 | None = None

    # TODO Check if Availability Types are coinciding at any point


class AvailabilityForScheduleSpec(AvailabilityBaseSpec):
    name: str
    slot_type: SlotTypeOptions
    slot_size_in_minutes: int | None = Field(ge=1)
    tokens_per_slot: int | None = Field(ge=1)
    create_tokens: bool = False
    reason: str = ""
    availability: list[AvailabilityDateTimeSpec]

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, availabilities: list[AvailabilityDateTimeSpec]):
        if has_overlapping_availability(availabilities):
            raise ValueError("Availability time ranges are overlapping")
        for availability in availabilities:
            if availability.start_time >= availability.end_time:
                raise ValueError("Start time must be earlier than end time")
        return availabilities

    @model_validator(mode="after")
    def validate_for_slot_type(self):
        if self.slot_type == "appointment":
            if not self.slot_size_in_minutes:
                raise ValueError(
                    "Slot size in minutes is required for appointment slots"
                )
            if not self.tokens_per_slot:
                raise ValueError("Tokens per slot is required for appointment slots")

            for availability in self.availability:
                start_time = datetime.datetime.combine(
                    datetime.datetime.now(tz=UTC).date(), availability.start_time
                )
                end_time = datetime.datetime.combine(
                    datetime.datetime.now(tz=UTC).date(), availability.end_time
                )
                availability_duration_in_seconds = (
                    end_time - start_time
                ).total_seconds()
                slot_size_in_seconds = self.slot_size_in_minutes * 60
                total_slots = availability_duration_in_seconds / slot_size_in_seconds
                if total_slots > settings.MAX_SLOTS_PER_AVAILABILITY:
                    error_message = f"Too many slots per availability. Maximum allowed is {settings.MAX_SLOTS_PER_AVAILABILITY} slots per availability session."
                    raise ValueError(error_message)
                if availability_duration_in_seconds % slot_size_in_seconds != 0:
                    raise ValueError(
                        "Availability duration must be a multiple of slot size in minutes"
                    )
        else:
            self.slot_size_in_minutes = None
            self.tokens_per_slot = None
        return self


class AvailabilityCreateSpec(AvailabilityForScheduleSpec):
    schedule: UUID4

    @model_validator(mode="after")
    def check_for_overlaps(self):
        availabilities = Availability.objects.filter(
            schedule__external_id=self.schedule
        )
        all_availabilities = [*self.availability]
        for availability in availabilities:
            all_availabilities.extend(
                [
                    AvailabilityDateTimeSpec(
                        day_of_week=availability["day_of_week"],
                        start_time=availability["start_time"],
                        end_time=availability["end_time"],
                    )
                    for availability in availability.availability
                ]
            )
        if has_overlapping_availability(all_availabilities):
            raise ValueError("Availability time ranges are overlapping")
        return self


class ScheduleBaseSpec(EMRResource):
    __model__ = Schedule
    __exclude__ = ["resource", "facility"]

    id: UUID4 | None = None


class ScheduleCreateSpec(ScheduleBaseSpec):
    user: UUID4
    facility: UUID4
    name: str
    valid_from: datetime.datetime
    valid_to: datetime.datetime
    availabilities: list[AvailabilityForScheduleSpec]

    @field_validator("valid_from", "valid_to")
    @classmethod
    def validate_dates(cls, value):
        now = care_now().replace(tzinfo=None)
        if value < now:
            raise ValueError("Date cannot be before the current date")
        return value

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_from > self.valid_to:
            raise ValueError("Valid from cannot be greater than valid to")
        return self

    @field_validator("availabilities")
    @classmethod
    def validate_availabilities_not_overlapping(
        cls, availabilities: list[AvailabilityForScheduleSpec]
    ):
        all_availabilities = []
        for availability in availabilities:
            all_availabilities.extend(availability.availability)
        if has_overlapping_availability(all_availabilities):
            raise ValueError("Availability time ranges are overlapping")
        return availabilities

    def perform_extra_deserialization(self, is_update, obj):
        user = get_object_or_404(User, external_id=self.user)
        # TODO Validation that user is in given facility
        obj.facility = Facility.objects.get(external_id=self.facility)

        resource, _ = SchedulableUserResource.objects.get_or_create(
            facility=obj.facility,
            user=user,
        )
        obj.resource = resource
        obj.availabilities = self.availabilities


class ScheduleUpdateSpec(ScheduleBaseSpec):
    name: str
    valid_from: datetime.datetime
    valid_to: datetime.datetime

    def perform_extra_deserialization(self, is_update, obj):
        old_instance = Schedule.objects.get(id=obj.id)

        # Get sum of allocated tokens in old date range
        old_allocated_sum = (
            TokenSlot.objects.filter(
                resource=old_instance.resource,
                availability__schedule__id=obj.id,
                start_datetime__gte=old_instance.valid_from,
                start_datetime__lte=old_instance.valid_to,
            ).aggregate(total=Sum("allocated"))["total"]
            or 0
        )

        # Get sum of allocated tokens in new validity range
        new_allocated_sum = (
            TokenSlot.objects.filter(
                resource=old_instance.resource,
                availability__schedule__id=obj.id,
                start_datetime__gte=self.valid_from,
                start_datetime__lte=self.valid_to,
            ).aggregate(total=Sum("allocated"))["total"]
            or 0
        )

        if old_allocated_sum != new_allocated_sum:
            msg = (
                "Cannot modify schedule validity as it would exclude some allocated slots. "
                f"Old range has {old_allocated_sum} allocated slots while new range has {new_allocated_sum} allocated slots."
            )
            raise ValidationError(msg)


class ScheduleReadSpec(ScheduleBaseSpec):
    name: str
    valid_from: datetime.datetime
    valid_to: datetime.datetime
    availabilities: list = []
    created_by: UserSpec = {}
    updated_by: UserSpec = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)

        mapping["availabilities"] = [
            AvailabilityForScheduleSpec.serialize(o)
            for o in Availability.objects.filter(schedule=obj)
        ]


def has_overlapping_availability(availabilities: list[AvailabilityDateTimeSpec]):
    for i in range(len(availabilities)):
        for j in range(i + 1, len(availabilities)):
            # Skip checking for overlap if it's not the same day of week
            if availabilities[i].day_of_week != availabilities[j].day_of_week:
                continue
            # Check if time ranges overlap
            if (
                availabilities[i].start_time <= availabilities[j].end_time
                and availabilities[j].start_time <= availabilities[i].end_time
            ):
                return True
    return False
