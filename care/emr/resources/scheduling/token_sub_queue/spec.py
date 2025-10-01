from enum import Enum

from pydantic import UUID4

from care.emr.models.scheduling.token import TokenSubQueue
from care.emr.resources.base import EMRResource
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions


class TokenSubQueueStatusOptions(str, Enum):
    active = "active"
    inactive = "inactive"


class TokenSubQueueBaseSpec(EMRResource):
    __model__ = TokenSubQueue
    __exclude__ = []

    id: UUID4 | None = None
    name: str
    status: TokenSubQueueStatusOptions


class TokenSubQueueCreateSpec(TokenSubQueueBaseSpec):
    resource_type: SchedulableResourceTypeOptions
    resource_id: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj._resource_type = self.resource_type  # noqa SLF001
        obj._resource_id = self.resource_id  # noqa SLF001


class TokenSubQueueReadSpec(TokenSubQueueBaseSpec):
    current_token: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.scheduling.token.spec import TokenMinimalSpec

        mapping["id"] = obj.external_id
        if obj.current_token:
            mapping["current_token"] = TokenMinimalSpec.serialize(
                obj.current_token
            ).to_json()
