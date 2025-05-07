from django.db import models

from care.emr.models import EMRBaseModel


class FacilityReportTemplate(EMRBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, db_index=True)
    config = models.JSONField(default=dict)
