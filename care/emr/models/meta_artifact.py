from django.db import models

from care.emr.models import EMRBaseModel


class MetaArtifact(EMRBaseModel):
    associating_type = models.CharField(max_length=255, null=False)
    associating_external_id = models.UUIDField(null=False)
    name = models.CharField(max_length=255)
    object_type = models.CharField(max_length=255)
    object_value = models.JSONField()
    note = models.TextField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=["associating_type", "associating_external_id"]),
        ]
