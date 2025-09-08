import datetime
from enum import Enum

from pydantic import UUID4, BaseModel

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product import Product
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.base import EMRResource
from care.emr.resources.charge_item_definition.spec import ChargeItemDefinitionReadSpec
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeReadSpec


class ProductStatusOptions(str, Enum):
    active = "active"
    inactive = "inactive"
    entered_in_error = "entered_in_error"


class ProductBatch(BaseModel):
    lot_number: str | None = None


class BaseProductSpec(EMRResource):
    """Base model for healthcare service"""

    __model__ = Product
    __exclude__ = ["product_knowledge", "charge_item_definition"]

    id: UUID4 | None = None
    status: ProductStatusOptions
    batch: ProductBatch | None = None
    expiration_date: datetime.datetime | None = None


class ProductWriteSpec(BaseProductSpec):
    """Payment reconciliation write specification"""

    product_knowledge: str
    charge_item_definition: str | None = None

    def perform_extra_deserialization(self, is_update, obj):
        obj.product_knowledge = ProductKnowledge.objects.get(
            slug=self.product_knowledge
        )
        if self.charge_item_definition:
            obj.charge_item_definition = ChargeItemDefinition.objects.get(
                slug=self.charge_item_definition
            )


class ProductUpdateSpec(BaseProductSpec):
    """Payment reconciliation write specification"""

    charge_item_definition: str | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.charge_item_definition:
            obj.charge_item_definition = ChargeItemDefinition.objects.get(
                slug=self.charge_item_definition
            )


class ProductReadSpec(BaseProductSpec):
    """Invoice read specification"""

    product_knowledge: dict
    charge_item_definition: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["product_knowledge"] = ProductKnowledgeReadSpec.serialize(
            obj.product_knowledge
        ).to_json()
        if obj.charge_item_definition:
            mapping["charge_item_definition"] = ChargeItemDefinitionReadSpec.serialize(
                obj.charge_item_definition
            ).to_json()
