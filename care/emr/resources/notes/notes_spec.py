import datetime

from django.utils import timezone
from pydantic import UUID4

from care.emr.models.notes import NoteMessage
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec


class NoteMessageSpec(EMRResource):
    __model__ = NoteMessage
    __exclude__ = ["thread"]
    id: UUID4 | None = None
    message: str


class NoteMessageCreateSpec(NoteMessageSpec):
    pass


class NoteMessageUpdateSpec(NoteMessageSpec):
    def perform_extra_deserialization(self, is_update, obj):
        old_obj = NoteMessage.objects.get(external_id=obj.external_id)
        if not obj.message_history:
            obj.message_history["history"] = []
        obj.message_history["history"].append(
            {
                "message": old_obj.message,
                "created_by": {
                    "username": old_obj.created_by.username,
                    "external_id": str(old_obj.created_by.external_id),
                },
                "edited_at": str(timezone.now()),
                "created_at": str(old_obj.modified_date),
            }
        )


class NoteMessageReadSpec(NoteMessageSpec):
    message_history: dict

    created_by: UserSpec = dict
    updated_by: UserSpec = dict
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
