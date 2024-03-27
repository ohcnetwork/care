import jsonschema
from django.db import models

from care.utils.models.base import BaseModel

form_data_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "friendlyName": {"type": "string"},
            "id": {"type": "string"},
            "default": {"type": "string"},
            "description": {"type": "string"},
            "type": {"type": "string"},
            "example": {"type": "string"},
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "anyOf": [
                                {"type": "integer"},
                                {"type": "string"},
                            ]
                        },
                        "text": {"type": "string"},
                    },
                    "required": ["id", "text"],
                },
            },
        },
        "required": ["friendlyName", "id", "description", "type", "example", "default"],
    },
}


def validate_json_schema(value):
    try:
        jsonschema.validate(value, form_data_schema)
    except jsonschema.exceptions.ValidationError as e:
        raise jsonschema.ValidationError(f"Invalid JSON data: {e}")


class AIFormFill(BaseModel):
    class Status(models.TextChoices):
        CREATED = "CREATED"
        READY = "READY"
        GENERATING_TRANSCRIPT = "GENERATING_TRANSCRIPT"
        GENERATING_AI_RESPONSE = "GENERATING_AI_RESPONSE"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    requested_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
    )
    form_data = models.JSONField(
        validators=[validate_json_schema], null=True, blank=True
    )
    transcript = models.TextField(null=True, blank=True)
    ai_response = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=50, choices=Status.choices, default=Status.CREATED
    )

    @property
    def audio_file_ids(self):
        from care.facility.models.file_upload import FileUpload

        return FileUpload.objects.filter(
            associating_id=self.external_id,
            file_type=FileUpload.FileType.AI.value,
            upload_completed=True,
            is_archived=False,
        ).values_list("external_id", flat=True)
