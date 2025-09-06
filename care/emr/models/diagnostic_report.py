from django.db import models

from care.emr.models.base import EMRBaseModel


class DiagnosticReport(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=255)
    category = models.JSONField(null=True, blank=True)
    code = models.JSONField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    conclusion = models.TextField(null=True, blank=True)
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey("emr.Encounter", on_delete=models.CASCADE)
    service_request = models.ForeignKey("emr.ServiceRequest", on_delete=models.CASCADE)
