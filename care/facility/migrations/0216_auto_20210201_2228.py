# Generated by Django 2.2.11 on 2021-02-01 16:58

import uuid

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0034_auto_20201122_2013"),
        ("facility", "0215_auto_20210130_2236"),
    ]

    operations = [
        migrations.CreateModel(
            name="DistrictScopedSummary",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, null=True)),
                (
                    "s_type",
                    models.CharField(
                        choices=[("PatientSummary", "PatientSummary")], max_length=100
                    ),
                ),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="LocalBodyScopedSummary",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, null=True)),
                (
                    "s_type",
                    models.CharField(
                        choices=[("PatientSummary", "PatientSummary")], max_length=100
                    ),
                ),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="facilityrelatedsummary",
            index=models.Index(
                fields=["-modified_date"], name="facility_fa_modifie_552c15_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="facilityrelatedsummary",
            index=models.Index(
                fields=["-created_date"], name="facility_fa_created_adc5be_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="facilityrelatedsummary",
            index=models.Index(fields=["s_type"], name="facility_fa_s_type_7b0ae3_idx"),
        ),
        migrations.AddIndex(
            model_name="facilityrelatedsummary",
            index=models.Index(
                fields=["-created_date", "s_type"],
                name="facility_fa_created_81979e_idx",
            ),
        ),
        migrations.AddField(
            model_name="localbodyscopedsummary",
            name="lsg",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="users.LocalBody",
            ),
        ),
        migrations.AddField(
            model_name="districtscopedsummary",
            name="district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="users.District",
            ),
        ),
        migrations.AddIndex(
            model_name="localbodyscopedsummary",
            index=models.Index(
                fields=["-modified_date"], name="facility_lo_modifie_a60b84_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="localbodyscopedsummary",
            index=models.Index(
                fields=["-created_date"], name="facility_lo_created_0e69e8_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="localbodyscopedsummary",
            index=models.Index(fields=["s_type"], name="facility_lo_s_type_f5b38c_idx"),
        ),
        migrations.AddIndex(
            model_name="localbodyscopedsummary",
            index=models.Index(
                fields=["-created_date", "s_type"],
                name="facility_lo_created_d5c5c0_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="districtscopedsummary",
            index=models.Index(
                fields=["-modified_date"], name="facility_di_modifie_09d187_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="districtscopedsummary",
            index=models.Index(
                fields=["-created_date"], name="facility_di_created_74064b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="districtscopedsummary",
            index=models.Index(fields=["s_type"], name="facility_di_s_type_7410ec_idx"),
        ),
        migrations.AddIndex(
            model_name="districtscopedsummary",
            index=models.Index(
                fields=["-created_date", "s_type"],
                name="facility_di_created_45003b_idx",
            ),
        ),
    ]
