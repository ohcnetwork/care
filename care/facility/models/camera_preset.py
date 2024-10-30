from django.db import models

from care.utils.models.base import BaseModel
from care.utils.models.validators import JSONFieldSchemaValidator

CAMERA_PRESET_POSITION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "x": {"type": "number"},
        "y": {"type": "number"},
        "zoom": {"type": "number"},
    },
    "required": ["x", "y", "zoom"],
    "additionalProperties": False,
}


class CameraPreset(BaseModel):
    name = models.CharField(max_length=255, null=True)
    asset_bed = models.ForeignKey(
        "facility.AssetBed", on_delete=models.PROTECT, related_name="camera_presets"
    )
    position = models.JSONField(
        validators=[JSONFieldSchemaValidator(CAMERA_PRESET_POSITION_SCHEMA)]
    )
    created_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    updated_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    is_migrated = models.BooleanField(default=False)
