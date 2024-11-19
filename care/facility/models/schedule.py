from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models

from care.facility.models.base import FacilityBaseModel
from care.facility.models.mixins.permissions.facility import (
    FacilityRelatedPermissionMixin,
)
from care.facility.models.patient_base import reverse_choices_with_label
from care.users.models import User


class SlotType(models.IntegerChoices):
    OPEN = 1, "Open"
    APPOINTMENT = 2, "Appointment"


REVERSE_SLOT_TYPE = reverse_choices_with_label(SlotType.choices)


class ScheduleResourceType(models.IntegerChoices):
    DOCTOR = 1, "Doctor"


RESOURCE_TO_MODEL = {
    ScheduleResourceType.DOCTOR: User,
}


class SchedulableResource(FacilityBaseModel):
    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, null=False, blank=False
    )
    resource_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    resource_id = models.PositiveIntegerField()
    resource = GenericForeignKey("resource_type", "resource_id")


class ScheduleBaseManager(models.Manager):
    def filter_by_resource(self, resource):
        return self.filter(
            resource__resource_id=resource.id,
            resource__resource_type=ContentType.objects.get_for_model(
                resource.__class__
            ),
        )


class Schedule(FacilityBaseModel, FacilityRelatedPermissionMixin):
    resource = models.ForeignKey(SchedulableResource, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=False, blank=False)
    valid_from = models.DateTimeField(null=False, blank=False)
    valid_to = models.DateTimeField(null=False, blank=False)

    objects = ScheduleBaseManager()


class Availability(FacilityBaseModel, FacilityRelatedPermissionMixin):
    schedule = models.ForeignKey(
        "Schedule", on_delete=models.CASCADE, null=False, blank=False
    )
    name = models.CharField(max_length=255, null=False, blank=False)
    slot_type = models.IntegerField(
        choices=SlotType.choices, default=SlotType.OPEN, null=False, blank=False
    )
    slot_size_in_minutes = models.IntegerField(null=False, blank=False, default=0)
    tokens_per_slot = models.IntegerField(null=False, blank=False, default=0)

    days_of_week = models.JSONField(default=list)
    start_time = models.TimeField(null=False, blank=False)
    end_time = models.TimeField(null=False, blank=False)

    def has_object_read_permission(self, request):
        return self.schedule.has_object_read_permission(request)

    def has_object_write_permission(self, request):
        return self.schedule.has_object_write_permission(request)


class ScheduleException(FacilityBaseModel, FacilityRelatedPermissionMixin):
    resource = models.ForeignKey(SchedulableResource, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=False, blank=False)

    slot_type = models.IntegerField(
        choices=SlotType.choices, default=SlotType.OPEN, null=False, blank=False
    )
    slot_size_in_minutes = models.IntegerField(null=False, blank=False, default=0)
    tokens_per_slot = models.IntegerField(null=False, blank=False, default=0)

    is_available = models.BooleanField(null=False, blank=False)
    datetime_range = DateTimeRangeField(null=False, blank=False)
