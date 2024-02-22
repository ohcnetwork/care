# Generated by Django 4.2.10 on 2024-02-22 09:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0414_remove_bed_old_name"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="patientconsultation",
            constraint=models.UniqueConstraint(
                fields=("patient_no", "facility"),
                name="unique_patient_no_within_facility",
            ),
        ),
    ]
