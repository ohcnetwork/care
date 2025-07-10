from django.db import models

from care.emr.models import EMRBaseModel


class SpecimenDefinition(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    version = models.IntegerField(default=1)
    slug = models.CharField(max_length=255)
    title = models.CharField(max_length=1024)
    derived_from_uri = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=255)
    description = models.TextField()
    type_collected = models.JSONField(null=True, blank=True)
    patient_preparation = models.JSONField(default=list)
    collection = models.JSONField(null=True, blank=True)
    type_tested = models.JSONField(default=dict)
