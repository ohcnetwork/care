import datetime
from decimal import Decimal
from enum import Enum

from django.conf import settings
from jsonschema import validate
from pydantic import UUID4, BaseModel, Field, field_validator

from care.emr.extensions.base import ExtensionResource
from care.emr.extensions.validator import ExtensionValidator
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product import Product
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.base import EMRResource
from care.emr.resources.charge_item_definition.spec import ChargeItemDefinitionReadSpec
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeReadSpec
from care.utils.shortcuts import get_object_or_404


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
    ___extension_resource_type__ = ExtensionResource.product

    id: UUID4 | None = None
    status: ProductStatusOptions
    batch: ProductBatch | None = None
    expiration_date: datetime.datetime | None = None
    extensions: dict
    standard_pack_size: int | None = None
    purchase_price: Decimal | None = Field(None, max_digits=20, decimal_places=6)

    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, v):
        try:
            validate(v, settings.PRODUCT_EXTENSIONS_JSON_SCHEMA)
        except Exception as e:
            raise ValueError("Invalid additional metadata") from e
        return v


class ProductWriteSpec(ExtensionValidator, BaseProductSpec):
    """Payment reconciliation write specification"""

    product_knowledge: str
    charge_item_definition: str | None = None

    def perform_extra_deserialization(self, is_update, obj):
        obj.product_knowledge = get_object_or_404(
            ProductKnowledge, slug=self.product_knowledge
        )
        if self.charge_item_definition:
            obj.charge_item_definition = get_object_or_404(
                ChargeItemDefinition, slug=self.charge_item_definition
            )


class ProductUpdateSpec(ExtensionValidator, BaseProductSpec):
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
