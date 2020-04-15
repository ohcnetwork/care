# Generated by Django 2.2.11 on 2020-04-14 16:36

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("facility", "0088_patientconsultationicmr_patienticmr_patientsampleicmr"),
        ("users", "0022_auto_verify_users_with_facility"),
    ]

    operations = [
        migrations.CreateModel(
            name="TestingLab",
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
                ("name", models.CharField(max_length=200)),
                ("address", models.TextField()),
                (
                    "pincode",
                    models.IntegerField(
                        validators=[
                            django.core.validators.RegexValidator(
                                code="invalid_pincode",
                                message="Please enter a valid pincode.",
                                regex="^(\\d{6}$)",
                            )
                        ]
                    ),
                ),
                (
                    "phone_number",
                    phonenumber_field.modelfields.PhoneNumberField(
                        max_length=128, region=None
                    ),
                ),
                (
                    "testing_capacity_per_day",
                    models.IntegerField(blank=True, default=0),
                ),
                (
                    "district",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="users.District",
                    ),
                ),
                (
                    "local_body",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="users.LocalBody",
                    ),
                ),
                (
                    "state",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="users.State",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
