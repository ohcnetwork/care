# Generated by Django 4.2.10 on 2024-05-21 11:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0431_patientnotes_thread"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="patientconsultation",
            name="unique_patient_no_within_facility",
        ),
        migrations.AddConstraint(
            model_name="patientconsultation",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("patient_no__isnull", False),
                    ("suggestion", "A"),
                    ("discharge_date__isnull", False),
                ),
                fields=("patient_no", "facility"),
                name="unique_patient_no_within_facility",
            ),
        ),
    ]
