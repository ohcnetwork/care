from pydantic import UUID4, Field

from care.emr.models.scheduling.token import TokenCategory
from care.emr.resources.base import EMRResource
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions


class TokenCategoryBaseSpec(EMRResource):
    __model__ = TokenCategory
    __exclude__ = []

    id: UUID4 | None = None
    name: str
    shorthand: str = Field(max_length=5)
    metadata: dict | None = None


class TokenCategoryUpdateSpec(TokenCategoryBaseSpec):
    pass


class TokenCategoryCreateSpec(TokenCategoryUpdateSpec):
    resource_type: SchedulableResourceTypeOptions


class TokenCategoryReadSpec(TokenCategoryBaseSpec):
    default: bool
    resource_type: SchedulableResourceTypeOptions

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class TokenCategoryRetrieveSpec(TokenCategoryReadSpec):
    created_by: dict = {}
    updated_by: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)
