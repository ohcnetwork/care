from django.db import models

from care.emr.models import EMRBaseModel


class SchedulableResource(EMRBaseModel):
    """A resource that can be scheduled for appointments."""

    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    resource_type = models.CharField(max_length=255, default="practitioner")
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, null=True, blank=True
    )
    location = models.ForeignKey(
        "emr.FacilityLocation", on_delete=models.CASCADE, null=True, blank=True
    )
    healthcare_service = models.ForeignKey(
        "emr.HealthcareService", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "resource_type", "user"],
                name="unique_facility_resource_user",
            ),
            models.UniqueConstraint(
                fields=["facility", "resource_type", "location"],
                name="unique_facility_resource_location",
            ),
            models.UniqueConstraint(
                fields=["facility", "resource_type", "healthcare_service"],
                name="unique_facility_resource_healthcare_service",
            ),
        ]


class Schedule(EMRBaseModel):
    resource = models.ForeignKey(SchedulableResource, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    charge_item_definition = models.ForeignKey(
        "emr.ChargeItemDefinition",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="schedule_charge_item_definition",
    )
    revisit_allowed_days = models.IntegerField(null=True, blank=True)
    revisit_charge_item_definition = models.ForeignKey(
        "emr.ChargeItemDefinition",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="schedule_revisit_charge_item_definition",
    )


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
    resource = models.ForeignKey(SchedulableResource, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    reason = models.TextField(null=True, blank=True)
    valid_from = models.DateField(null=False, blank=False)
    valid_to = models.DateField(null=False, blank=False)
    start_time = models.TimeField(null=False, blank=False)
    end_time = models.TimeField(null=False, blank=False)
