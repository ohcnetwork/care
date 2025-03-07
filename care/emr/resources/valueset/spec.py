from enum import Enum

from django.core.validators import slug_re
from pydantic import UUID4, Field, field_validator, model_validator

from care.emr.models.valueset import ValueSet as ValuesetDatabaseModel
from care.emr.resources.base import EMRResource
from care.emr.resources.common.valueset import ValueSetCompose
from care.emr.resources.user.spec import UserSpec


class ValueSetStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"
    unknown = "unknown"


class ValueSetBaseSpec(EMRResource):
    __model__ = ValuesetDatabaseModel

    id: UUID4 = None
    slug: str | None = Field(None, min_length=5, max_length=25, pattern=r"^[-\w]+$")
    name: str
    description: str
    compose: ValueSetCompose
    status: ValueSetStatusOptions
    is_system_defined: bool = False


class ValueSetSpec(ValueSetBaseSpec):
    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str, info):
        if not name.strip():
            raise ValueError("Name cannot be empty")
        return name.strip()

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, slug: str, info) -> str:
        if not slug_re.match(slug):
            err = "Slug must be alphanumeric and can contain hyphens, underscores, and periods."
            raise ValueError(err)
        queryset = ValuesetDatabaseModel.objects.filter(slug=slug)
        context = cls.get_serializer_context(info)
        if context.get("is_update", False):
            queryset = queryset.exclude(id=info.context["object"].id)
        if queryset.exists():
            err = "Slug must be unique"
            raise ValueError(err)
        return slug

    @model_validator(mode="after")
    def validate_slug_system(self):
        if not self.is_system_defined and "system-" in self.slug:
            err = "Cannot create valueset with system like slug"
            raise ValueError(err)
        return self

    def perform_extra_deserialization(self, is_update, obj):
        obj.compose = self.compose.model_dump(exclude_defaults=True, exclude_none=True)


class ValueSetReadSpec(ValueSetBaseSpec):
    created_by: UserSpec = dict
    updated_by: UserSpec = dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)


ValueSetSpec.model_rebuild()
