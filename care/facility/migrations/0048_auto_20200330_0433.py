# Generated by Django 2.2.11 on 2020-03-30 04:33

import django.core.validators
import django.db.models.deletion
import fernet_fields.fields
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0019_auto_20200328_2226"),
        ("facility", "0047_auto_20200329_1051"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientregistration",
            name="facility",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="facility.Facility",
            ),
        ),
        migrations.CreateModel(
            name="HistoricalPatientRegistration",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("name", fernet_fields.fields.EncryptedCharField(max_length=200)),
                ("age", models.PositiveIntegerField()),
                (
                    "gender",
                    models.IntegerField(
                        choices=[(1, "Male"), (2, "Female"), (3, "Non-binary")]
                    ),
                ),
                (
                    "phone_number",
                    fernet_fields.fields.EncryptedCharField(
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
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Not active when discharged, or removed from the watchlist",
                    ),
                ),
                ("deleted", models.BooleanField(default=False)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "district",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="users.District",
                    ),
                ),
                (
                    "facility",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="facility.Facility",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "local_body",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="users.LocalBody",
                    ),
                ),
                (
                    "state",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="users.State",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical patient registration",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
