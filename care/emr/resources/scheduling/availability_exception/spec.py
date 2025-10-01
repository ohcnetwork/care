import datetime

from pydantic import UUID4, field_validator, model_validator

from care.emr.models import AvailabilityException
from care.emr.resources.base import EMRResource
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.utils.time_util import care_now


class AvailabilityExceptionBaseSpec(EMRResource):
    __model__ = AvailabilityException
    __exclude__ = ["resource", "facility"]

    id: UUID4 | None = None
    reason: str | None = None
    valid_from: datetime.date
    valid_to: datetime.date
    start_time: datetime.time
    end_time: datetime.time


class AvailabilityExceptionWriteSpec(AvailabilityExceptionBaseSpec):
    facility: UUID4 | None = None
    resource_type: SchedulableResourceTypeOptions
    resource_id: UUID4

    @field_validator("valid_from", "valid_to")
    @classmethod
    def validate_dates(cls, value):
        now = care_now().date()
        if value < now:
            raise ValueError("Date cannot be before the current date")
        return value

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_from > self.valid_to:
            raise ValueError("Valid from cannot be greater than valid to")
        return self

    def perform_extra_deserialization(self, is_update, obj):
        obj._resource_type = self.resource_type  # noqa SLF001
        obj._resource_id = self.resource_id  # noqa SLF001


class AvailabilityExceptionReadSpec(AvailabilityExceptionBaseSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
