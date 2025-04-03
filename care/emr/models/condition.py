from django.db import models

from care.emr.models.base import EMRBaseModel


class Condition(EMRBaseModel):
    clinical_status = models.CharField(max_length=100, null=True, blank=True)
    verification_status = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    severity = models.CharField(max_length=100, null=True, blank=True)
    code = models.JSONField(default=dict, null=False, blank=False)
    body_site = models.JSONField(default=dict, null=False, blank=False)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, null=True, blank=True
    )
    onset = models.JSONField(default=dict)
    abatement = models.JSONField(default=dict)
    recorded_date = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
