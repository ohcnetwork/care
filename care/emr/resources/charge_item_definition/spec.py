from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.base import EMRResource
from care.emr.resources.common.monetary_component import MonetaryComponent
from care.emr.resources.resource_category.spec import ResourceCategoryReadSpec


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
    price_components: list[MonetaryComponent]
    category: str | None = None

    @field_validator("price_components")
    @classmethod
    def check_components_with_duplicate_codes(
        cls, price_components: list[MonetaryComponent]
    ):
        code_type_pairs = [
            (component.code.code, component.monetary_component_type)
            for component in price_components
            if component.code
        ]
        if len(code_type_pairs) != len(set(code_type_pairs)):
            raise ValueError("Same codes for the same component type are not allowed")
        return price_components

    def perform_extra_deserialization(self, is_update, obj):
        if self.category:
            obj.category = ResourceCategory.objects.get(slug=self.category)


class ChargeItemDefinitionReadSpec(ChargeItemDefinitionSpec):
    """ChargeItemDefinition read specification"""

    version: int | None = None
    category: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.category:
            mapping["category"] = ResourceCategoryReadSpec.serialize(
                obj.category
            ).to_json()
