import datetime
from enum import Enum

from django.core.exceptions import ObjectDoesNotExist
from pydantic import UUID4
from rest_framework.exceptions import ValidationError

from care.emr.models import AvailabilityException, TokenSlot
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
            try:
                user = User.objects.get(external_id=self.user)
                resource = SchedulableUserResource.objects.get(
                    user=user,
                    facility=Facility.objects.get(external_id=self.facility),
                )
                obj.resource = resource
            except ObjectDoesNotExist as e:
                raise ValidationError("Object does not exist") from e

        slots = TokenSlot.objects.filter(
            resource=obj.resource,
            start_datetime__date__gte=self.valid_from,
            start_datetime__date__lte=self.valid_to,
            start_datetime__time__gte=self.start_time,
            start_datetime__time__lte=self.end_time,
        )
        if slots.filter(allocated__gt=0):
            raise ValidationError("There are bookings during this exception")
        slots.delete()


class AvailabilityExceptionReadSpec(AvailabilityExceptionBaseSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
