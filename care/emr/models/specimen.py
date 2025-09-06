from django.db import models

from care.emr.models import EMRBaseModel


class Specimen(EMRBaseModel):
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        default=None,
        null=True,
        blank=True,
    )

    accession_identifier = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=20)
    specimen_type = models.JSONField()
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, null=True, blank=True
    )
    received_time = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    condition = models.JSONField(default=list)
    processing = models.JSONField(default=list)
    collection = models.JSONField(default=dict)
    service_request = models.ForeignKey(
        "emr.ServiceRequest", on_delete=models.CASCADE, null=True, blank=True
    )
    specimen_definition = models.ForeignKey(
        "emr.SpecimenDefinition", on_delete=models.CASCADE, null=True, blank=True
    )
