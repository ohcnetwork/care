from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0309_patienthealthdetails"),
    ]

    operations = [
        migrations.AddField(
            model_name="patienthealthdetails",
            name="allergies",
            field=models.TextField(
                blank=True, default="", verbose_name="Patient's Known Allergies"
            ),
        ),
        migrations.AddField(
            model_name="patienthealthdetails",
            name="blood_group",
            field=models.CharField(
                choices=[
                    ("A+", "A+"),
                    ("A-", "A-"),
                    ("B+", "B+"),
                    ("B-", "B-"),
                    ("AB+", "AB+"),
                    ("AB-", "AB-"),
                    ("O+", "O+"),
                    ("O-", "O-"),
                    ("UNK", "UNKNOWN"),
                ],
                max_length=4,
                null=True,
                verbose_name="Blood Group of Patient",
            ),
        ),
        migrations.AddField(
            model_name="patienthealthdetails",
            name="has_allergy",
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveField(
            model_name="historicalpatientregistration",
            name="allergies",
        ),
        migrations.RemoveField(
            model_name="historicalpatientregistration",
            name="blood_group",
        ),
        migrations.RemoveField(
            model_name="patientregistration",
            name="allergies",
        ),
        migrations.RemoveField(
            model_name="patientregistration",
            name="blood_group",
        ),
    ]
