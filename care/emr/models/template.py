from django.db import models

from care.emr.models import EMRBaseModel


class FacilityReportTemplate(EMRBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    config = models.JSONField(default=dict)
