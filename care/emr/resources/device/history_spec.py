from datetime import datetime

from pydantic import UUID4

from care.emr.models import DeviceServiceHistory
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.user.spec import UserSpec


class DeviceServiceHistorySpecBase(EMRResource):
    __model__ = DeviceServiceHistory
    __exclude__ = ["device", "edit_history"]
    id: UUID4 | None = None


class DeviceServiceHistoryWriteSpec(DeviceServiceHistorySpecBase):
    serviced_on: datetime
    note: str


class DeviceServiceHistoryListSpec(DeviceServiceHistoryWriteSpec):
    created_date: datetime
    modified_date: datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class DeviceServiceHistoryRetrieveSpec(DeviceServiceHistoryListSpec):
    edit_history: list[dict] = []

    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)
        edit_history = []
        for history in obj.edit_history:
            user = history.get("updated_by")
            if user:
                history["updated_by"] = model_from_cache(UserSpec, id=user)
            else:
                history["updated_by"] = {}  # Edge Case
            edit_history.append(history)
        mapping["edit_history"] = edit_history
