from django.db import models

from care.emr.models import EMRBaseModel


class ReportTemplate(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.CASCADE, null=True, blank=True
    )
    type = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, db_index=True)
    config = models.JSONField(default=dict)
    derived_from_url = models.URLField(null=True, blank=True)
