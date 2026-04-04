import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("emr", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TranscriptionSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("recording", "Recording"),
                            ("transcribing", "Transcribing"),
                            ("generating_notes", "Generating Notes"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="created",
                        max_length=20,
                    ),
                ),
                ("duration_seconds", models.FloatField(default=0)),
                ("transcript", models.TextField(blank=True, default="")),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "encounter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transcription_sessions",
                        to="emr.encounter",
                    ),
                ),
                (
                    "initiated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transcription_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_date"]},
        ),
        migrations.CreateModel(
            name="TranscriptionSegment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                ("text", models.TextField()),
                ("start_time", models.FloatField(help_text="Start time in seconds")),
                ("end_time", models.FloatField(help_text="End time in seconds")),
                ("confidence", models.FloatField(default=0.0)),
                (
                    "speaker",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Speaker label if diarization is available",
                        max_length=50,
                    ),
                ),
                ("is_final", models.BooleanField(default=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="segments",
                        to="ai_voice.transcriptionsession",
                    ),
                ),
            ],
            options={"ordering": ["start_time"]},
        ),
        migrations.CreateModel(
            name="SOAPNote",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("generating", "Generating"),
                            ("completed", "Completed"),
                            ("reviewed", "Reviewed"),
                            ("failed", "Failed"),
                        ],
                        default="generating",
                        max_length=20,
                    ),
                ),
                ("subjective", models.TextField(blank=True, default="")),
                ("objective", models.TextField(blank=True, default="")),
                ("assessment", models.TextField(blank=True, default="")),
                ("plan", models.TextField(blank=True, default="")),
                ("summary", models.TextField(blank=True, default="", help_text="Brief clinical summary")),
                ("raw_response", models.JSONField(blank=True, default=dict, help_text="Raw LLM response for debugging")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="soap_notes",
                        to="ai_voice.transcriptionsession",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_soap_notes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_date"]},
        ),
    ]
