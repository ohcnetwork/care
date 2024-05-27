from email.utils import localtime

from django.db import migrations
from django.utils.timezone import now


class Migration(migrations.Migration):
    def archive_deleted_consents(apps, schema_editor):
        PatientConsultation = apps.get_model("facility", "PatientConsultation")
        FileUpload = apps.get_model("facility", "FileUpload")
        consultations = PatientConsultation.objects.all()

        consent_records = []
        for consultation in consultations:
            new_consent_records = list(
                filter(lambda x: x.get("deleted", False), consultation.consent_records)
            )
            consent_records.extend(new_consent_records)

        files = FileUpload.objects.filter(
            associating_id__in=[x["id"] for x in consent_records],
            is_archived=False,
        )
        for file in files:
            file.is_archived = True
            file.archive_reason = "Consent Record Deleted"
            file.archived_datetime = localtime(now())
            file.archived_by = consultation.last_edited_by
            file.save()

    def noop(apps, schema_editor):
        pass

    dependencies = [
        ("facility", "0438_alter_dailyround_patient_category_and_more"),
    ]

    operations = [
        migrations.RunPython(archive_deleted_consents, reverse_code=noop),
    ]
