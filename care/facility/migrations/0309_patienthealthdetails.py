import care.facility.models.mixins.permissions.patient
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("facility", "0308_auto_20220805_2247"),
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
                    models.UUIDField(db_index=True, default=uuid.uuid4, unique=True),
                ),
                (
                    "created_date",
                    models.DateTimeField(auto_now_add=True, db_index=True, null=True),
                ),
                (
                    "modified_date",
                    models.DateTimeField(auto_now=True, db_index=True, null=True),
                ),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "family_details",
                    models.TextField(
                        blank=True, default="", verbose_name="Patient's Family Details"
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
            ],
            options={
                "abstract": False,
            },
            bases=(
                models.Model,
                care.facility.models.mixins.permissions.patient.PatientRelatedPermissionMixin,
            ),
        ),
    ]
