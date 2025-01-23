from django.db import models
from django.utils import timezone

from care.emr.models.base import EMRBaseModel


class MedicationRequest(EMRBaseModel):
    status = models.CharField(max_length=100, null=True, blank=True)
    status_reason = models.CharField(max_length=100, null=True, blank=True)
    intent = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    priority = models.CharField(max_length=100, null=True, blank=True)
    do_not_perform = models.BooleanField()
    method = models.JSONField(default=dict, null=True, blank=True)
    medication = models.JSONField(default=dict, null=True, blank=True)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey("emr.Encounter", on_delete=models.CASCADE)
    dosage_instruction = models.JSONField(default=list, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    authored_on = models.DateTimeField(null=True, blank=True, default=timezone.now)
    requester = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True
    )
