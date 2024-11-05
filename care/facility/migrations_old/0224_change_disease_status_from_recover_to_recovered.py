from django.db import migrations

from care.facility.models.patient_base import DiseaseStatusChoices


def change_recovery_to_recovered(apps, schema_editor):
    PatientRegistration = apps.get_model("facility", "PatientRegistration")
    PatientRegistration.objects.filter(
        disease_status=DiseaseStatusChoices.RECOVERY.value
    ).update(disease_status=DiseaseStatusChoices.RECOVERED.value)


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0223_merge_20210427_1419"),
    ]
    operations = [
        migrations.RunPython(change_recovery_to_recovered, migrations.RunPython.noop),
    ]
