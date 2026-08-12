from datetime import datetime
from enum import Enum

from pydantic import UUID4, Field
from pydantic.experimental.missing_sentinel import MISSING

from care.emr.models.action import Action
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityReadSpec


class ActionContextOptions(str, Enum):
    APPOINTMENT = "APPOINTMENT"
    PATIENT = "PATIENT"


class BaseActionConfigurationSpec(EMRResource):
    """Base model for activity definition"""

    __model__ = Action

    id: UUID4 | None = None
    name: str = Field(max_length=254)
    description: str | MISSING = MISSING
    actions: list[dict]


class ActionConfigurationWriteSpec(BaseActionConfigurationSpec):
    performable: bool
    action_context: ActionContextOptions
    # facility: UUID4 | None = None


class ActionConfigurationUpdateSpec(BaseActionConfigurationSpec):
    name: str | MISSING = Field(MISSING, max_length=254)
    description: str | MISSING = MISSING
    actions: list[dict] | MISSING = MISSING


class ActionConfigurationReadSpec(BaseActionConfigurationSpec):
    performable: bool
    action_context: ActionContextOptions
    facility: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["facility"] = (
            FacilityReadSpec.serialize(obj.facility).to_json() if obj.facility else None
        )


class ActionConfigurationRetrieveSpec(ActionConfigurationReadSpec):
    created_date: datetime
    modified_date: datetime
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)
