# Generated by Django 2.2.11 on 2020-03-29 07:49

import fernet_fields.fields
from django.db import migrations


def populate_real_names(apps, *args):
    Patient = apps.get_model("facility", "PatientRegistration")

    patients = Patient.objects.all()
    # check to be done, else may cause issues for new people or during migration revert
    if patients and hasattr(patients[0], "real_name"):
        for p in patients:
            p.real_name = p.name
            p.save()


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0043_populate_facility_district"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientregistration",
            name="real_name",
            field=fernet_fields.fields.EncryptedCharField(
                default="real name", max_length=200
            ),
            preserve_default=False,
        ),
        migrations.RunPython(populate_real_names),
    ]
