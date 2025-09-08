import datetime

from pydantic import UUID4

from care.emr.models.scheduling.token import TokenQueue
from care.emr.resources.base import EMRResource
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions


class TokenQueueBaseSpec(EMRResource):
    __model__ = TokenQueue
    __exclude__ = []

    id: UUID4 | None = None
    name: str


class TokenQueueCreateSpec(TokenQueueBaseSpec):
    resource_type: SchedulableResourceTypeOptions
    resource_id: UUID4
    date: datetime.date

    def perform_extra_deserialization(self, is_update, obj):
        obj._resource_type = self.resource_type  # noqa SLF001
        obj._resource_id = self.resource_id  # noqa SLF001


class TokenQueueUpdateSpec(TokenQueueBaseSpec):
    pass


class TokenQueueReadSpec(TokenQueueBaseSpec):
    date: datetime.date
    is_primary: bool
    system_generated: bool
    date: datetime.date

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class TokenQueueRetrieveSpec(TokenQueueReadSpec):
    created_by: dict = {}
    updated_by: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)
