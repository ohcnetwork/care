import datetime
from enum import Enum

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
        # Validates if availability overlaps for the same day
        for i in range(len(availabilities)):
            for j in range(i + 1, len(availabilities)):
                if availabilities[i].day_of_week != availabilities[j].day_of_week:
                    continue
                # Check if time ranges overlap
                if (
                    availabilities[i].start_time <= availabilities[j].end_time
                    and availabilities[j].start_time <= availabilities[i].end_time
                ):
                    raise ValueError("Availability time ranges are overlapping")
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
        else:
            self.slot_size_in_minutes = None
            self.tokens_per_slot = None
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

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_from > self.valid_to:
            raise ValidationError("Valid from cannot be greater than valid to")
        return self

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
