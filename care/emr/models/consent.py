from django.db import models

from care.emr.models import EMRBaseModel


class Consent(EMRBaseModel):
    status = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    date = models.DateTimeField()
    period = models.JSONField(default=dict)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, related_name="consents"
    )
    decision = models.CharField(max_length=10)
    verification_details = models.JSONField(default=list)
    note = models.TextField(null=True, blank=True)
