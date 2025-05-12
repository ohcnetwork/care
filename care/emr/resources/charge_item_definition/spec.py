from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.resources.base import EMRResource
from care.emr.resources.common.monetary_component import MonetaryComponent


class ChargeItemDefinitionStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"


class ChargeItemDefinitionSpec(EMRResource):
    """Base model for ChargeItemDefinition"""

    __model__ = ChargeItemDefinition
    __exclude__ = []

    id: UUID4 | None = None
    status: ChargeItemDefinitionStatusOptions
    title: str
    slug: str
    derived_from_uri: str | None = None
    description: str | None = None
    purpose: str | None = None
    price_component: list[MonetaryComponent]

    @field_validator("price_component")
    @classmethod
    def check_components_with_duplicate_codes(
        cls, price_component: list[MonetaryComponent]
    ):
        code_type_pairs = [
            (component.code.code, component.monetary_component_type)
            for component in price_component
            if component.code
        ]
        if len(code_type_pairs) != len(set(code_type_pairs)):
            raise ValueError("Same codes for the same component type are not allowed")
        return price_component


class ChargeItemDefinitionReadSpec(ChargeItemDefinitionSpec):
    """ChargeItemDefinition read specification"""

    version: int | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
