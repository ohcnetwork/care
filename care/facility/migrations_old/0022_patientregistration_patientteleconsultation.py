# Generated by Django 2.2.11 on 2020-03-24 17:48

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("facility", "0021_auto_20200324_0756"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientTeleConsultation",
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
                    "symptoms",
                    models.CharField(
                        choices=[
                            (1, "NO"),
                            (2, "FEVER"),
                            (3, "SORE THROAT"),
                            (4, "COUGH"),
                            (5, "BREATHLESSNESS"),
                        ],
                        max_length=9,
                    ),
                ),
                ("other_symptoms", models.TextField(blank=True, null=True)),
                (
                    "reason",
                    models.TextField(
                        blank=True, null=True, verbose_name="Reason for calling"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PatientRegistration",
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
                ("age", models.PositiveIntegerField()),
                (
                    "gender",
                    models.IntegerField(
                        choices=[(1, "Male"), (2, "Female"), (3, "Other")]
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        max_length=14,
                        validators=[
                            django.core.validators.RegexValidator(
                                code="invalid_mobile",
                                message="Please Enter 10/11 digit mobile number or landline as 0<std code><phone number>",
                                regex="^((\\+91|91|0)[\\- ]{0,1})?[456789]\\d{9}$",
                            )
                        ],
                    ),
                ),
                (
                    "contact_with_carrier",
                    models.BooleanField(verbose_name="Contact with a Covid19 carrier"),
                ),
                (
                    "medical_history",
                    models.CharField(
                        choices=[
                            (1, "NO"),
                            (2, "Diabetes"),
                            (3, "Heart Disease"),
                            (4, "HyperTension"),
                            (5, "Kidney Diseases"),
                        ],
                        max_length=9,
                    ),
                ),
                ("medical_history_details", models.TextField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
