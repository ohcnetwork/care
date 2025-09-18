from enum import Enum

from pydantic import UUID4

from care.emr.models.resource_category import ResourceCategory
from care.emr.resources.base import EMRResource
from care.emr.utils.slug_type import SlugType


class ResourceCategoryResourceTypeOptions(str, Enum):
    product_knowledge = "product_knowledge"
    activity_definition = "activity_definition"
    charge_item_definition = "charge_item_definition"


class ResourceCategoryBaseSpec(EMRResource):
    """Base model for ChargeItemDefinition"""

    __model__ = ResourceCategory
    __exclude__ = ["parent"]

    id: UUID4 | None = None
    title: str
    description: str | None = None
    resource_type: ResourceCategoryResourceTypeOptions
    resource_sub_type: str


class ResourceCategoryUpdateSpec(ResourceCategoryBaseSpec):
    slug_value: SlugType

    def perform_extra_deserialization(self, is_update, obj):
        obj.slug = self.slug_value


class ResourceCategoryWriteSpec(ResourceCategoryBaseSpec):
    """ChargeItemDefinition Category write specification"""

    parent: str | None = None
    is_child: bool = False
    slug_value: SlugType

    def perform_extra_deserialization(self, is_update, obj):
        if self.parent:
            obj.parent = ResourceCategory.objects.get(slug=self.parent)
        obj.slug = self.slug_value


class ResourceCategoryReadSpec(ResourceCategoryBaseSpec):
    """ChargeItemDefinition Category write specification"""

    parent: dict
    has_children: bool
    level_cache: int = 0
    is_child: bool
    slug_config: dict
    slug: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["parent"] = obj.get_parent_json()
        mapping["slug_config"] = obj.parse_slug(obj.slug)
