import enum

from django.db import migrations, models


class OccupationEnum(enum.Enum):
    STUDENT = 1
    MEDICAL_WORKER = 2
    GOVT_EMPLOYEE = 3
    PRIVATE_EMPLOYEE = 4
    HOME_MAKER = 5
    WORKING_ABROAD = 6
    OTHERS = 7


OccupationChoices = [(item.value, item.name) for item in OccupationEnum]
occupation_list = []


def get_occupation(apps, schema_editor):
    PatientRegistration = apps.get_model("facility", "PatientRegistration")
    patients = PatientRegistration.objects.all()

    for patient in patients:
        occupation = ""

        if patient.meta_info and patient.meta_info.occupation:
            occupation = OccupationChoices[patient.meta_info.occupation]

            occupation_list.append(
                {
                    "patient": patient,
                    "occupation": occupation,
                }
            )


def populate_occupation(apps, schema_editor):
    PatientRegistration = apps.get_model("facility", "PatientRegistration")

    for occupation in occupation_list:
        patient = PatientRegistration.objects.get(id=occupation["patient"].id)
        patient.meta_info.occupation = occupation["occupation"][1]
        patient.meta_info.save()


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0372_assetavailabilityrecord"),
    ]

    operations = [
        migrations.RunPython(get_occupation, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="patientmetainfo",
            name="occupation",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RunPython(populate_occupation, migrations.RunPython.noop),
    ]
