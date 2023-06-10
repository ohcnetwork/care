from uuid import uuid4

from django.db import migrations


def unique_patient_external_ids(apps, *args):
    Patient = apps.get_model("facility", "PatientRegistration")
    for patient in Patient.objects.all():
        patient.external_id = uuid4()
        patient.save()


def reverse_unique_patient_external_ids(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0103_auto_20200425_1440"),
    ]

    operations = [
        migrations.RunPython(
            unique_patient_external_ids,
            reverse_code=reverse_unique_patient_external_ids,
        )
    ]
