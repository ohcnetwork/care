# Generated by Django 4.2.15 on 2024-09-06 05:21

from django.core.paginator import Paginator
from django.db import migrations, models
from django.db.models import Q

import care.utils.models.validators


def replace_io_balance_name(instance, find, replace):
    for entry in instance.infusions:
        if entry["name"] == find:
            entry["name"] = replace

    for entry in instance.iv_fluids:
        if entry["name"] == find:
            entry["name"] = replace

    for entry in instance.feeds:
        if entry["name"] == find:
            entry["name"] = replace

    for entry in instance.output:
        if entry["name"] == find:
            entry["name"] = replace


class Migration(migrations.Migration):
    """
    1. Improves JSON Schema Validation of JSON Fields in DailyRounds model.
    2. Fills name with "Unknown" for I/O balance field items for ones with
       empty string.
    3. Update blood pressure column to `None` for empty objects (`{}`).
    """

    dependencies = [
        ("facility", "0456_dailyround_appetite_dailyround_bladder_drainage_and_more"),
    ]

    def forward_fill_empty_io_balance_field_names(apps, schema_editor):
        DailyRound = apps.get_model("facility", "DailyRound")

        paginator = Paginator(
            DailyRound.objects.filter(
                Q(infusions__contains=[{"name": ""}])
                | Q(iv_fluids__contains=[{"name": ""}])
                | Q(feeds__contains=[{"name": ""}])
                | Q(output__contains=[{"name": ""}])
            ).order_by("id"),
            1000,
        )

        for page_number in paginator.page_range:
            bulk = []
            for instance in paginator.page(page_number).object_list:
                replace_io_balance_name(instance, find="", replace="Unknown")
                bulk.append(instance)
            DailyRound.objects.bulk_update(
                bulk, ["infusions", "iv_fluids", "feeds", "output"]
            )

    def reverse_fill_empty_io_balance_field_names(apps, schema_editor):
        DailyRound = apps.get_model("facility", "DailyRound")

        paginator = Paginator(
            DailyRound.objects.filter(
                Q(infusions__contains=[{"name": "Unknown"}])
                | Q(iv_fluids__contains=[{"name": "Unknown"}])
                | Q(feeds__contains=[{"name": "Unknown"}])
                | Q(output__contains=[{"name": "Unknown"}])
            ).order_by("id"),
            1000,
        )

        for page_number in paginator.page_range:
            bulk = []
            for instance in paginator.page(page_number).object_list:
                replace_io_balance_name(instance, find="Unknown", replace="")
                bulk.append(instance)
            DailyRound.objects.bulk_update(
                bulk, ["infusions", "iv_fluids", "feeds", "output"]
            )

    def forward_set_empty_bp_to_null(apps, schema_editor):
        DailyRound = apps.get_model("facility", "DailyRound")
        DailyRound.objects.filter(bp={}).update(bp=None)

    def reverse_set_empty_bp_to_null(apps, schema_editor):
        DailyRound = apps.get_model("facility", "DailyRound")
        DailyRound.objects.filter(bp=None).update(bp={})

    operations = [
        migrations.RunPython(
            forward_fill_empty_io_balance_field_names,
            reverse_code=reverse_fill_empty_io_balance_field_names,
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="bp",
            field=models.JSONField(
                default=None,
                null=True,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "additionalProperties": False,
                            "properties": {
                                "diastolic": {
                                    "maximum": 400,
                                    "minimum": 0,
                                    "type": "number",
                                },
                                "systolic": {
                                    "maximum": 400,
                                    "minimum": 0,
                                    "type": "number",
                                },
                            },
                            "required": ["systolic", "diastolic"],
                            "type": "object",
                        }
                    )
                ],
            ),
        ),
        migrations.RunPython(
            forward_set_empty_bp_to_null,
            reverse_code=reverse_set_empty_bp_to_null,
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="feeds",
            field=models.JSONField(
                default=list,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "items": [
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {"enum": ["Ryles Tube", "Normal Feed"]},
                                        "quantity": {"minimum": 0, "type": "number"},
                                    },
                                    "required": ["name", "quantity"],
                                    "type": "object",
                                }
                            ],
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="infusions",
            field=models.JSONField(
                default=list,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "items": [
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {
                                            "enum": [
                                                "Adrenalin",
                                                "Nor-adrenalin",
                                                "Vasopressin",
                                                "Dopamine",
                                                "Dobutamine",
                                            ]
                                        },
                                        "quantity": {"minimum": 0, "type": "number"},
                                    },
                                    "required": ["name", "quantity"],
                                    "type": "object",
                                }
                            ],
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="iv_fluids",
            field=models.JSONField(
                default=list,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "items": [
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {"enum": ["RL", "NS", "DNS"]},
                                        "quantity": {"minimum": 0, "type": "number"},
                                    },
                                    "required": ["name", "quantity"],
                                    "type": "object",
                                }
                            ],
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="nursing",
            field=models.JSONField(
                default=list,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "items": [
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "description": {"type": "string"},
                                        "procedure": {
                                            "enum": [
                                                "oral_care",
                                                "hair_care",
                                                "bed_bath",
                                                "eye_care",
                                                "perineal_care",
                                                "skin_care",
                                                "pre_enema",
                                                "wound_dressing",
                                                "lymphedema_care",
                                                "ascitic_tapping",
                                                "colostomy_care",
                                                "colostomy_change",
                                                "personal_hygiene",
                                                "positioning",
                                                "suctioning",
                                                "ryles_tube_care",
                                                "ryles_tube_change",
                                                "iv_sitecare",
                                                "nubulisation",
                                                "dressing",
                                                "dvt_pump_stocking",
                                                "restrain",
                                                "chest_tube_care",
                                                "tracheostomy_care",
                                                "tracheostomy_change",
                                                "stoma_care",
                                                "catheter_care",
                                                "catheter_change",
                                            ]
                                        },
                                    },
                                    "required": ["procedure", "description"],
                                    "type": "object",
                                }
                            ],
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="output",
            field=models.JSONField(
                default=list,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "items": [
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {
                                            "enum": [
                                                "Urine",
                                                "Ryles Tube Aspiration",
                                                "ICD",
                                                "Abdominal Drain",
                                            ]
                                        },
                                        "quantity": {"minimum": 0, "type": "number"},
                                    },
                                    "required": ["name", "quantity"],
                                    "type": "object",
                                }
                            ],
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="pain_scale_enhanced",
            field=models.JSONField(
                default=list,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "items": [
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "description": {"type": "string"},
                                        "region": {
                                            "enum": [
                                                "AnteriorHead",
                                                "AnteriorNeck",
                                                "AnteriorRightShoulder",
                                                "AnteriorRightChest",
                                                "AnteriorRightArm",
                                                "AnteriorRightForearm",
                                                "AnteriorRightHand",
                                                "AnteriorLeftHand",
                                                "AnteriorLeftChest",
                                                "AnteriorLeftShoulder",
                                                "AnteriorLeftArm",
                                                "AnteriorLeftForearm",
                                                "AnteriorRightFoot",
                                                "AnteriorLeftFoot",
                                                "AnteriorRightLeg",
                                                "AnteriorLowerChest",
                                                "AnteriorAbdomen",
                                                "AnteriorLeftLeg",
                                                "AnteriorRightThigh",
                                                "AnteriorLeftThigh",
                                                "AnteriorGroin",
                                                "PosteriorHead",
                                                "PosteriorNeck",
                                                "PosteriorLeftChest",
                                                "PosteriorRightChest",
                                                "PosteriorAbdomen",
                                                "PosteriorLeftShoulder",
                                                "PosteriorRightShoulder",
                                                "PosteriorLeftArm",
                                                "PosteriorLeftForearm",
                                                "PosteriorLeftHand",
                                                "PosteriorRightArm",
                                                "PosteriorRightForearm",
                                                "PosteriorRightHand",
                                                "PosteriorLeftThighAndButtock",
                                                "PosteriorRightThighAndButtock",
                                                "PosteriorLeftLeg",
                                                "PosteriorRightLeg",
                                                "PosteriorLeftFoot",
                                                "PosteriorRightFoot",
                                            ]
                                        },
                                        "scale": {
                                            "maximum": 10,
                                            "minimum": 1,
                                            "type": "number",
                                        },
                                    },
                                    "required": ["region", "scale"],
                                    "type": "object",
                                }
                            ],
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="dailyround",
            name="pressure_sore",
            field=models.JSONField(
                default=list,
                validators=[
                    care.utils.models.validators.JSONFieldSchemaValidator(
                        {
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "items": [
                                {
                                    "additionalProperties": False,
                                    "properties": {
                                        "description": {"type": "string"},
                                        "exudate_amount": {
                                            "enum": [
                                                "None",
                                                "Light",
                                                "Moderate",
                                                "Heavy",
                                            ]
                                        },
                                        "length": {"minimum": 0, "type": "number"},
                                        "push_score": {
                                            "maximum": 19,
                                            "minimum": 0,
                                            "type": "number",
                                        },
                                        "region": {
                                            "enum": [
                                                "AnteriorHead",
                                                "AnteriorNeck",
                                                "AnteriorRightShoulder",
                                                "AnteriorRightChest",
                                                "AnteriorRightArm",
                                                "AnteriorRightForearm",
                                                "AnteriorRightHand",
                                                "AnteriorLeftHand",
                                                "AnteriorLeftChest",
                                                "AnteriorLeftShoulder",
                                                "AnteriorLeftArm",
                                                "AnteriorLeftForearm",
                                                "AnteriorRightFoot",
                                                "AnteriorLeftFoot",
                                                "AnteriorRightLeg",
                                                "AnteriorLowerChest",
                                                "AnteriorAbdomen",
                                                "AnteriorLeftLeg",
                                                "AnteriorRightThigh",
                                                "AnteriorLeftThigh",
                                                "AnteriorGroin",
                                                "PosteriorHead",
                                                "PosteriorNeck",
                                                "PosteriorLeftChest",
                                                "PosteriorRightChest",
                                                "PosteriorAbdomen",
                                                "PosteriorLeftShoulder",
                                                "PosteriorRightShoulder",
                                                "PosteriorLeftArm",
                                                "PosteriorLeftForearm",
                                                "PosteriorLeftHand",
                                                "PosteriorRightArm",
                                                "PosteriorRightForearm",
                                                "PosteriorRightHand",
                                                "PosteriorLeftThighAndButtock",
                                                "PosteriorRightThighAndButtock",
                                                "PosteriorLeftLeg",
                                                "PosteriorRightLeg",
                                                "PosteriorLeftFoot",
                                                "PosteriorRightFoot",
                                            ]
                                        },
                                        "scale": {
                                            "maximum": 5,
                                            "minimum": 1,
                                            "type": "number",
                                        },
                                        "tissue_type": {
                                            "enum": [
                                                "Closed",
                                                "Epithelial",
                                                "Granulation",
                                                "Slough",
                                                "Necrotic",
                                            ]
                                        },
                                        "width": {"minimum": 0, "type": "number"},
                                    },
                                    "required": ["region", "width", "length"],
                                    "type": "object",
                                }
                            ],
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
    ]
