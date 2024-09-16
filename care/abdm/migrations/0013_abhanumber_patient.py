# Generated by Django 4.2.10 on 2024-04-21 09:33

import django.db.models.deletion
from django.db import migrations, models
from django.db.models.expressions import RawSQL


class Migration(migrations.Migration):
    def reverse_patient_abhanumber_relation(apps, schema_editor):
        Patient = apps.get_model("facility", "PatientRegistration")
        AbhaNumber = apps.get_model("abdm", "AbhaNumber")

        patients = (
            Patient.objects.annotate(removed_field=RawSQL("abha_number_id", ()))
            .filter(abha_number__isnull=False)
            .select_related("abha_number")
        )
        abha_numbers_to_update = []

        for patient in patients:
            abha_number = patient.abha_number
            abha_number.patient = patient
            abha_numbers_to_update.append(abha_number)

        AbhaNumber.objects.bulk_update(abha_numbers_to_update, ["patient"])

    dependencies = [
        ("facility", "0432_alter_fileupload_file_type"),
        ("abdm", "0012_consentrequest_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="abhanumber",
            name="patient",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="abha_number",
                to="facility.patientregistration",
            ),
        ),
        migrations.RunPython(
            code=reverse_patient_abhanumber_relation,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
