import uuid

from django.db import models

from care.utils.models.base import BaseModel


class TranscriptionSession(BaseModel):
    """A real-time transcription session linked to a patient encounter."""

    class Status(models.TextChoices):
        CREATED = "created"
        RECORDING = "recording"
        TRANSCRIBING = "transcribing"
        GENERATING_NOTES = "generating_notes"
        COMPLETED = "completed"
        FAILED = "failed"

    encounter = models.ForeignKey(
        "emr.Encounter",
        on_delete=models.CASCADE,
        related_name="transcription_sessions",
    )
    initiated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="transcription_sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )
    duration_seconds = models.FloatField(default=0)
    transcript = models.TextField(blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"TranscriptionSession {self.external_id} ({self.status})"


class TranscriptionSegment(BaseModel):
    """An individual transcribed segment from a session."""

    session = models.ForeignKey(
        TranscriptionSession,
        on_delete=models.CASCADE,
        related_name="segments",
    )
    text = models.TextField()
    start_time = models.FloatField(help_text="Start time in seconds")
    end_time = models.FloatField(help_text="End time in seconds")
    confidence = models.FloatField(default=0.0)
    speaker = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Speaker label if diarization is available",
    )
    is_final = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"Segment [{self.start_time:.1f}s]: {self.text[:60]}"


class SOAPNote(BaseModel):
    """AI-generated SOAP note from a transcription session."""

    class Status(models.TextChoices):
        GENERATING = "generating"
        COMPLETED = "completed"
        REVIEWED = "reviewed"
        FAILED = "failed"

    session = models.ForeignKey(
        TranscriptionSession,
        on_delete=models.CASCADE,
        related_name="soap_notes",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.GENERATING,
    )
    subjective = models.TextField(blank=True, default="")
    objective = models.TextField(blank=True, default="")
    assessment = models.TextField(blank=True, default="")
    plan = models.TextField(blank=True, default="")
    summary = models.TextField(
        blank=True,
        default="",
        help_text="Brief clinical summary",
    )
    raw_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw LLM response for debugging",
    )
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_soap_notes",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"SOAPNote {self.external_id} ({self.status})"
