import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import partial_index
import care.facility.models.mixins.permissions.patient
import care.utils.models.validators


def create_health_details(apps, schema_editor):
    health_details = apps.get_model("facility", "PatientHealthDetails")
    patient_registration = apps.get_model("facility", "PatientRegistration")
    patients = patient_registration.objects.all()

    health_details_objs = []
    for patient in patients:
        has_allergy = False
        allergies = ""
        blood_group = None
        consultation = None
        facility = patient.facility
        weight = 0.0
        height = 0.0

        if patient.allergies:
            has_allergy = True
            allergies = patient.allergies

        if patient.blood_group is not None:
            blood_group = patient.blood_group

        if patient.last_consultation is not None:
            facility = patient.last_consultation.facility
            consultation = patient.last_consultation

            if patient.last_consultation.weight is not None:
                weight = patient.last_consultation.weight
            if patient.last_consultation.height is not None:
                height = patient.last_consultation.height

        health_details_obj = health_details(
            patient=patient,
            facility=facility,
            weight=weight,
            height=height,
            consultation=consultation,
            has_allergy=has_allergy,
            allergies=allergies,
            blood_group=blood_group,
        )

        health_details_objs.append(health_details_obj)

    health_details.objects.bulk_create(health_details_objs)


def link_data(apps, schema_editor):
    patient_consultation = apps.get_model("facility", "PatientConsultation")
    health_details = apps.get_model("facility", "PatientHealthDetails")
    patient_cons_objs = patient_consultation.objects.all()

    for patient_cons in patient_cons_objs:
        patient_cons.last_health_details = health_details.objects.get(
            id=patient_cons.patient.id
        )
        patient_cons.save(update_fields=["last_health_details"])


def create_vaccination_history(apps, schema_editor):
    vaccination_history = apps.get_model("facility", "VaccinationHistory")
    patient_registration = apps.get_model("facility", "PatientRegistration")
    patients = patient_registration.objects.all()

    vaccine_objs = []
    for patient in patients:
        if (
            patient.vaccine_name
            and patient.last_consultation.last_health_details
        ):
            vaccine_objs.append(
                vaccination_history(
                    health_details=patient.last_consultation.last_health_details,
                    vaccine=patient.vaccine_name,
                    doses=patient.number_of_doses,
                    date=patient.last_vaccinated_date,
                    precision=0,
                )
            )

    vaccination_history.objects.bulk_create(vaccine_objs)


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0321_merge_20220921_2255"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientHealthDetails",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, unique=True
                    ),
                ),
                (
                    "created_date",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, null=True
                    ),
                ),
                (
                    "modified_date",
                    models.DateTimeField(
                        auto_now=True, db_index=True, null=True
                    ),
                ),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "family_details",
                    models.TextField(
                        blank=True,
                        default="",
                        verbose_name="Patient's Family Details",
                    ),
                ),
                (
                    "facility",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="health_details",
                        to="facility.Facility",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="health_details",
                        to="facility.PatientRegistration",
                    ),
                ),
                (
                    "has_allergy",
                    models.BooleanField(default=False),
                ),
                (
                    "allergies",
                    models.TextField(
                        blank=True,
                        default="",
                        verbose_name="Patient's Known Allergies",
                    ),
                ),
                (
                    "blood_group",
                    models.CharField(
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
                (
                    "consultation",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="facility.PatientConsultation",
                    ),
                ),
                (
                    "weight",
                    models.FloatField(
                        default=None,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0)
                        ],
                        verbose_name="Patient's Weight in KG",
                    ),
                ),
                (
                    "height",
                    models.FloatField(
                        default=None,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0)
                        ],
                        verbose_name="Patient's Height in CM",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(
                models.Model,
                care.facility.models.mixins.permissions.patient.PatientRelatedPermissionMixin,
            ),
        ),
        migrations.CreateModel(
            name="VaccinationHistory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("vaccine", models.CharField(max_length=100)),
                ("doses", models.IntegerField(default=0)),
                ("date", models.DateField(blank=True, null=True)),
                ("precision", models.IntegerField(default=0)),
                ("deleted", models.BooleanField(default=False)),
                (
                    "health_details",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vaccination_history",
                        to="facility.PatientHealthDetails",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="patientconsultation",
            name="last_health_details",
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="facility.PatientHealthDetails",
            ),
        ),
        migrations.AddIndex(
            model_name="vaccinationhistory",
            index=partial_index.PartialIndex(
                fields=["health_details", "vaccine"],
                name="facility_va_health__5bb62d_partial",
                unique=True,
                where=partial_index.PQ(deleted=False),
            ),
        ),
        migrations.RunPython(create_health_details, migrations.RunPython.noop),
        migrations.RunPython(link_data, migrations.RunPython.noop),
        migrations.RunPython(
            create_vaccination_history, migrations.RunPython.noop
        ),
    ]
