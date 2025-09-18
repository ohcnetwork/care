from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models.base import SlugBaseModel


class ActivityDefinition(SlugBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT)
    version = models.IntegerField(default=1)
    slug = models.CharField(max_length=255)
    title = models.CharField(max_length=1024)
    classification = models.CharField(max_length=100)
    derived_from_uri = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=255)
    description = models.TextField()
    usage = models.TextField()
    kind = models.CharField(max_length=100)
    code = models.JSONField(null=True, blank=True)
    body_site = models.JSONField(null=True, blank=True)
    specimen_requirements = ArrayField(models.IntegerField(), default=list)
    observation_result_requirements = ArrayField(models.IntegerField(), default=list)
    locations = ArrayField(models.IntegerField(), default=list)
    latest = models.BooleanField(default=True)  # True when its the latest version
    charge_item_definitions = ArrayField(models.IntegerField(), default=list)
    diagnostic_report_codes = models.JSONField(null=True, blank=True)
    healthcare_service = models.ForeignKey(
        "emr.HealthcareService",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    tags = ArrayField(models.IntegerField(), default=list)
    category = models.ForeignKey(
        "emr.ResourceCategory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
