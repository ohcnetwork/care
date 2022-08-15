from django.db import migrations, models


def populate_data(apps, schema_editor):
    HealthDetails = apps.get_model("facility", "PatientHealthDetails")
    PatientRegistration = apps.get_model("facility", "PatientRegistration")
    patients = PatientRegistration.objects.all()

    health_details_objs = []
    for patient in patients:
        has_allergy = False
        allergies = ""
        blood_group = None

        if patient.allergies:
            has_allergy = True
            allergies = patient.allergies

        if patient.blood_group is not None:
            blood_group = patient.blood_group

        health_details_objs.append(
            HealthDetails(
                patient=patient,
                facility=patient.facility,
                has_allergy=has_allergy,
                allergies=allergies,
                blood_group=blood_group,
            )
        )

    HealthDetails.objects.bulk_create(health_details_objs)


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
        migrations.RunPython(populate_data, migrations.RunPython.noop),
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
