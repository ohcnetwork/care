from django.db import models

from care.emr.models import EMRBaseModel


class NoteThread(EMRBaseModel):
    title = models.CharField(max_length=255, null=True, blank=True)
    thread_type = models.CharField(max_length=100, default="patient")
    patient = models.ForeignKey("emr.Patient", on_delete=models.CASCADE)
    encounter = models.ForeignKey(
        "emr.Encounter", on_delete=models.CASCADE, null=True, blank=True
    )
    # TODO Add organizations to further restrict access


class NoteMessage(EMRBaseModel):
    thread = models.ForeignKey(NoteThread, on_delete=models.CASCADE)
    message = models.TextField()
    message_history = models.JSONField(default=dict)
