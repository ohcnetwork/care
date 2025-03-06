from datetime import datetime
from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models import MetaArtifact
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec


class MetaArtifactAssociatingTypeChoices(str, Enum):
    patient = "patient"
    encounter = "encounter"


class MetaArtifactObjectTypeChoices(str, Enum):
    drawing = "drawing"


class MetaArtifactBaseSpec(EMRResource):
    __model__ = MetaArtifact

    id: UUID4 | None = None
    object_value: dict | list
    note: str | None = None


class MetaArtifactUpdateSpec(MetaArtifactBaseSpec):
    pass


class MetaArtifactReadSpec(MetaArtifactBaseSpec):
    associating_type: MetaArtifactAssociatingTypeChoices
    associating_id: UUID4
    object_type: MetaArtifactObjectTypeChoices
    name: str
    created_date: datetime
    modified_date: datetime
    created_by: UserSpec
    updated_by: UserSpec

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)


class MetaArtifactCreateSpec(MetaArtifactBaseSpec):
    associating_type: MetaArtifactAssociatingTypeChoices
    associating_id: UUID4
    object_type: MetaArtifactObjectTypeChoices
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str):
        if not name.strip():
            raise ValueError("Name cannot be empty")
        return name

    def perform_extra_deserialization(self, is_update, obj):
        obj.associating_external_id = self.associating_id
