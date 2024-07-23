from django.db import models

from care.utils.models.base import BaseModel
from care.utils.models.validators import JSONFieldSchemaValidator

CAMERA_PRESET_POSITION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "x": {"type": "number"},
        "y": {"type": "number"},
        "z": {"type": "number"},
    },
    "additionalProperties": False,
}

CAMERA_PRESET_BOUNDARY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "x0": {"type": "number"},
        "y0": {"type": "number"},
        "x1": {"type": "number"},
        "y1": {"type": "number"},
    },
    "additionalProperties": False,
}


class CameraPreset(BaseModel):
    name = models.CharField(max_length=255, null=True)
    asset_bed = models.ForeignKey(
        "facility.AssetBed", on_delete=models.PROTECT, related_name="camera_presets"
    )

    position = models.JSONField(
        validators=[JSONFieldSchemaValidator(CAMERA_PRESET_POSITION_SCHEMA)], null=True
    )
    boundary = models.JSONField(
        validators=[JSONFieldSchemaValidator(CAMERA_PRESET_BOUNDARY_SCHEMA)], null=True
    )

    created_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    updated_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    is_migrated = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="position_xor_boundary",
                check=(
                    models.Q(position__isnull=False, boundary__isnull=True)
                    | models.Q(position__isnull=True, boundary__isnull=False)
                ),
            ),
            models.UniqueConstraint(
                name="single_boundary_preset_for_assetbed",
                fields=("asset_bed",),
                condition=models.Q(boundary__isnull=False, deleted=False),
            ),
        ]
