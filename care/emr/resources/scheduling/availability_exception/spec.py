import datetime
from enum import Enum

from django.core.exceptions import ObjectDoesNotExist
from pydantic import UUID4
from rest_framework.exceptions import ValidationError

from care.emr.models import AvailabilityException
from care.emr.models.scheduling.schedule import SchedulableUserResource
from care.emr.resources.base import EMRResource
from care.facility.models import Facility
from care.users.models import User


class ResourceTypeOptions(str, Enum):
    user = "user"


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
    user: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            resource = None
            try:
                user = User.objects.get(external_id=self.user)
                resource = SchedulableUserResource.objects.get(
                    user=user,
                    facility=Facility.objects.get(external_id=self.facility),
                )
                obj.resource = resource
            except ObjectDoesNotExist as e:
                raise ValidationError("Object does not exist") from e


class AvailabilityExceptionReadSpec(AvailabilityExceptionBaseSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
