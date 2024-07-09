# Generated by Django 4.2.10 on 2024-07-09 01:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0444_alter_medicineadministration_dosage_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyround",
            name="patient_category",
            field=models.CharField(
                choices=[
                    ("Comfort", "Comfort Care"),
                    ("Stable", "Mild"),
                    ("Moderate", "Moderate"),
                    ("Critical", "Critical"),
                    ("ActivelyDying", "ActivelyDying"),
                ],
                max_length=13,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="patientconsultation",
            name="category",
            field=models.CharField(
                choices=[
                    ("Comfort", "Comfort Care"),
                    ("Stable", "Mild"),
                    ("Moderate", "Moderate"),
                    ("Critical", "Critical"),
                    ("ActivelyDying", "ActivelyDying"),
                ],
                max_length=13,
                null=True,
            ),
        ),
    ]
