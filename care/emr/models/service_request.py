from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models.base import EMRBaseModel


class ServiceRequest(EMRBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT)
    title = models.CharField(max_length=1024)
    category = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    intent = models.CharField(max_length=255)
    priority = models.CharField(max_length=255)
    do_not_perform = models.BooleanField(default=False)
    note = models.TextField(null=True, blank=True)
    occurance = models.DateTimeField(null=True, blank=True)
    patient_instruction = models.TextField(null=True, blank=True)
    code = models.JSONField(null=True, blank=True)
    body_site = models.JSONField(null=True, blank=True)
    locations = ArrayField(models.IntegerField(), default=list)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, null=True, blank=True
    )
    healthcare_service = models.ForeignKey(
        "emr.HealthcareService",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    activity_definition = models.ForeignKey(
        "emr.ActivityDefinition",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    requester = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        default=None,
        null=True,
        blank=True,
    )
    tags = ArrayField(models.IntegerField(), default=list)
