from django.db import models

from care.emr.models.base import EMRBaseModel


class Procedure(EMRBaseModel):
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey("emr.Encounter", on_delete=models.CASCADE)
    status = models.CharField(max_length=100)
    status_reason = models.JSONField(null=True, blank=True)
    category = models.JSONField(default=list)
    code = models.JSONField(default=dict)
    occurrence = models.JSONField(default=dict)
    recorded_date = models.DateTimeField(null=True, blank=True)
    is_primary_source = models.BooleanField(default=False)
    body_site = models.JSONField(default=list)
    reason = models.JSONField(default=list)
    outcome = models.CharField(max_length=32, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
