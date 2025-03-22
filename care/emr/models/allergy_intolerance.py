from django.db import models

from care.emr.models.base import EMRBaseModel


class AllergyIntolerance(EMRBaseModel):
    clinical_status = models.CharField(max_length=100, null=True, blank=True)
    verification_status = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    criticality = models.CharField(max_length=100, null=True, blank=True)
    code = models.JSONField(default=dict, null=False, blank=False)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey("emr.Encounter", on_delete=models.CASCADE)
    onset = models.JSONField(default=dict)
    recorded_date = models.DateTimeField(null=True, blank=True)
    last_occurrence = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    copied_from = models.BigIntegerField(
        default=None, null=True, blank=True
    )  # If True, the record is a copy maintained of the given ID
    allergy_intolerance_type = models.CharField(max_length=20, default="allergy")
