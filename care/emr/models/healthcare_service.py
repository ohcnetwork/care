from django.contrib.postgres.fields import ArrayField
from django.db import models

from care.emr.models import EMRBaseModel


class HealthcareService(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    styling_metadata = models.JSONField(null=True, blank=True)
    name = models.CharField(max_length=1024)
    service_type = models.JSONField(default=dict)
    internal_type = models.CharField(
        max_length=255, null=True, blank=True, default=None
    )
    locations = ArrayField(models.IntegerField(), default=list)
    extra_details = models.TextField()
    managing_organization = models.ForeignKey(
        "emr.FacilityOrganization",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
