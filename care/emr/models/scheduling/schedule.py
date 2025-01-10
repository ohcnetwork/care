from django.db import models

from care.emr.models import EMRBaseModel


class SchedulableUserResource(EMRBaseModel):
    """A resource that can be scheduled for appointments."""

    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)

    # TODO : Index with resource and facility


class Schedule(EMRBaseModel):
    resource = models.ForeignKey(SchedulableUserResource, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()


class Availability(EMRBaseModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slot_type = models.CharField()
    slot_size_in_minutes = models.IntegerField(null=True, blank=False)
    tokens_per_slot = models.IntegerField(null=True, blank=False)
    create_tokens = models.BooleanField(default=False)
    reason = models.TextField(null=True, blank=True)
    availability = models.JSONField(default=dict)


class AvailabilityException(EMRBaseModel):
    resource = models.ForeignKey(SchedulableUserResource, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    reason = models.TextField(null=True, blank=True)
    valid_from = models.DateField(null=False, blank=False)
    valid_to = models.DateField(null=False, blank=False)
    start_time = models.TimeField(null=False, blank=False)
    end_time = models.TimeField(null=False, blank=False)
