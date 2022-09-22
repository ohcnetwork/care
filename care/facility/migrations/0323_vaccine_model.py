import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import partial_index


def create_vaccination_data(apps, schema_editor):
    patient_health_details = apps.get_model("facility", "PatientHealthDetails")
    vaccine = apps.get_model("facility", "Vaccine")
    health_details_objs = patient_health_details.objects.all()
    vaccine_objs = []

    for health_detail in health_details_objs:
        vaccine_objs.append(
            vaccine(
                health_details=health_detail,
                vaccine=health_detail.patient.vaccine_name,
                doses=health_detail.patient.number_of_doses,
                last_vaccinated_date=health_detail.patient.last_vaccinated_date,
            )
        )

    vaccine.objects.bulk_create(vaccine_objs)


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0322_patienthealthdetails"),
    ]

    operations = [
        migrations.CreateModel(
            name="Vaccine",
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
                    "vaccine",
                    models.CharField(
                        choices=[
                            ("CoviShield", "COVISHIELD"),
                            ("Covaxin", "COVAXIN"),
                            ("Sputnik", "SPUTNIK"),
                            ("Moderna", "MODERNA"),
                            ("Pfizer", "PFIZER"),
                            ("Janssen", "JANSSEN"),
                            ("Sinovac", "SINOVAC"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "doses",
                    models.PositiveIntegerField(
                        default=0,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(3),
                        ],
                    ),
                ),
                (
                    "last_vaccinated_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Date Last Vaccinated",
                    ),
                ),
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
        migrations.AddIndex(
            model_name="vaccine",
            index=partial_index.PartialIndex(
                fields=["health_details", "vaccine"],
                name="facility_va_health__0b97b3_partial",
                unique=True,
                where=partial_index.PQ(deleted=False),
            ),
        ),
        migrations.RunPython(
            create_vaccination_data, migrations.RunPython.noop
        ),
    ]
