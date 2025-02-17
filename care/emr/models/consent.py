from django.db import models

from care.emr.models import EMRBaseModel


class Consent(EMRBaseModel):
    status = models.CharField(max_length=50)
    category = models.JSONField(default=list)
    date = models.DateTimeField()
    period = models.JSONField(null=True, blank=True)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, related_name="consents"
    )
    decision = models.CharField(max_length=10)
    # source_attachment = # need to think more about it
    verification_details = models.JSONField(null=True, blank=True)
