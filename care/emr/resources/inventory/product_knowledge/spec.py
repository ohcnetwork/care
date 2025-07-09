from enum import Enum

from pydantic import UUID4, BaseModel

from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.base import EMRResource
from care.emr.resources.common.coding import Coding
from care.emr.resources.specimen.spec import DurationSpec
from care.facility.models.facility import Facility


class ProductTypeOptions(str, Enum):
    medication = "medication"
    nutritional_product = "nutritional_product"
    consumable = "consumable"


class ProductNameTypes(str, Enum):
    trade_name = "trade_name"
    alias = "alias"
    original_name = "original_name"
    preferred = "preferred"


class ProductKnowledgeStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"
    unknown = "unknown"


class ProductName(BaseModel):
    name_type: ProductNameTypes
    name: str


class StorageGuideline(BaseModel):
    note: str
    stability_duration: DurationSpec


class ProductDefinitionSpec(BaseModel):
    dosage_form: Coding
    intended_routes: list[Coding]
    ingredients: list[dict]
    nutrients: list[dict]
    drug_characteristic: dict


class BaseProductKnowledgeSpec(EMRResource):
    """Base model for healthcare service"""

    __model__ = ProductKnowledge
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    slug: str
    status: ProductKnowledgeStatusOptions
    product_type: ProductTypeOptions
    code: Coding | None = None
    base_unit: Coding | None = None
    name: str
    names: list[ProductName] = []
    storage_guidelines: list[StorageGuideline] = []
    definitional: ProductDefinitionSpec | None = None


class ProductKnowledgeWriteSpec(BaseProductKnowledgeSpec):
    """Payment reconciliation write specification"""

    facility: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = Facility.objects.get(external_id=self.facility)


class ProductKnowledgeReadSpec(BaseProductKnowledgeSpec):
    """Invoice read specification"""

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
