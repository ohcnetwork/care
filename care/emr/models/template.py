from django.db import models

from care.emr.models import EMRBaseModel
from care.facility.models import Facility


class FacilityReportTemplate(EMRBaseModel):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    config = models.JSONField(default=dict)
