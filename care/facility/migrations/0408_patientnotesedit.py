# Generated by Django 4.2.2 on 2023-08-28 14:09

import django.db.models.deletion
from django.conf import settings
from django.core.paginator import Paginator
from django.db import migrations, models


def create_initial_patient_notes_edit_record(apps, schema_editor):
    PatientNotes = apps.get_model("facility", "PatientNotes")
    PatientNotesEdit = apps.get_model("facility", "PatientNotesEdit")

    notes_without_edits = PatientNotes.objects.all()

    paginator = Paginator(notes_without_edits, 1000)
    for page_number in paginator.page_range:
        edit_records = []
        for patient_note in paginator.page(page_number).object_list:
            edit_record = PatientNotesEdit(
                patient_note=patient_note,
                edited_date=patient_note.created_date,
                edited_by=patient_note.created_by,
                note=patient_note.note,
            )

            edit_records.append(edit_record)

        PatientNotesEdit.objects.bulk_create(edit_records)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("facility", "0407_alter_dailyround_additional_symptoms_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientNotesEdit",
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
                ("edited_date", models.DateTimeField(auto_now_add=True)),
                ("note", models.TextField()),
                (
                    "edited_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "patient_note",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="edits",
                        to="facility.patientnotes",
                    ),
                ),
            ],
            options={
                "ordering": ["-edited_date"],
            },
        ),
        migrations.RunPython(
            code=create_initial_patient_notes_edit_record,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
