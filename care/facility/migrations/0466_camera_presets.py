# Generated by Django 4.2.8 on 2024-05-30 06:56

import uuid

import django.db.models.deletion
from django.conf import settings
from django.core.paginator import Paginator
from django.db import migrations, models
from django.db.models import F, Window
from django.db.models.functions import RowNumber

import care.utils.models.validators


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("facility", "0465_merge_20240923_1045"),
    ]

    def delete_asset_beds_without_asset_class(apps, schema_editor):
        AssetBed = apps.get_model("facility", "AssetBed")
        AssetBed.objects.filter(asset__asset_class__isnull=True).delete()

    def backfill_camera_presets(apps, schema_editor):
        AssetBed = apps.get_model("facility", "AssetBed")
        CameraPreset = apps.get_model("facility", "CameraPreset")

        paginator = Paginator(
            AssetBed.objects.annotate(
                row_number=Window(
                    expression=RowNumber(),
                    partition_by=[F("asset"), F("bed")],
                    order_by=F("id").asc(),
                )
            )
            .filter(deleted=False, asset__asset_class="ONVIF")
            .order_by("asset", "bed", "id"),
            1000,
        )

        for page_number in paginator.page_range:
            assetbeds_to_delete = []
            presets_to_create = []

            for asset_bed in paginator.page(page_number).object_list:
                name = asset_bed.meta.get("preset_name")

                if position := asset_bed.meta.get("position"):
                    presets_to_create.append(
                        CameraPreset(
                            name=name,
                            asset_bed=AssetBed.objects.filter(
                                asset=asset_bed.asset, bed=asset_bed.bed
                            ).order_by("id")[0],
                            position={
                                "x": position["x"],
                                "y": position["y"],
                                "zoom": position["zoom"],
                            },
                            is_migrated=True,
                        )
                    )
                    if asset_bed.row_number != 1:
                        assetbeds_to_delete.append(asset_bed.id)
                else:
                    assetbeds_to_delete.append(asset_bed.id)

            CameraPreset.objects.bulk_create(presets_to_create)
            AssetBed.objects.filter(id__in=assetbeds_to_delete).update(
                deleted=True, meta={}
            )
        AssetBed.objects.filter(deleted=False, asset__asset_class="ONVIF").update(
            meta={}
        )

    operations = [
        migrations.CreateModel(
            name="CameraPreset",
            fields=[
                (
                    "id",
                    models.BigAutoField(
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
                ("name", models.CharField(max_length=255, null=True)),
                (
                    "position",
                    models.JSONField(
                        validators=[
                            care.utils.models.validators.JSONFieldSchemaValidator(
                                {
                                    "$schema": "http://json-schema.org/draft-07/schema#",
                                    "additionalProperties": False,
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                        "zoom": {"type": "number"},
                                    },
                                    "required": ["x", "y", "zoom"],
                                    "type": "object",
                                }
                            )
                        ],
                    ),
                ),
                ("is_migrated", models.BooleanField(default=False)),
                (
                    "asset_bed",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="camera_presets",
                        to="facility.assetbed",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            delete_asset_beds_without_asset_class,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            backfill_camera_presets,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="assetbed",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted", False)),
                fields=("asset", "bed"),
                name="unique_together_asset_bed",
            ),
        ),
    ]
