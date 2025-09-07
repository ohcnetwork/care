from enum import Enum

from pydantic import UUID4, BaseModel

from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.base import EMRResource
from care.emr.resources.common.coding import Coding
from care.emr.resources.common.quantity import Quantity, Ratio
from care.emr.resources.inventory.product_knowledge.valueset import (
    CARE_NUTRIENTS_VALUESET,
    CARE_SUBSTANCE_VALUSET,
    MEDICATION_FORM_CODES,
)
from care.emr.resources.observation.valueset import CARE_UCUM_UNITS
from care.emr.resources.specimen.spec import DurationSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
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


class DrugCharacteristicCode(str, Enum):
    imprint_code = "imprint_code"
    size = "size"
    shape = "shape"
    color = "color"
    coating = "coating"
    scoring = "scoring"
    logo = "logo"
    image = "image"


class ProductName(BaseModel):
    name_type: ProductNameTypes
    name: str


class StorageGuideline(BaseModel):
    note: str
    stability_duration: DurationSpec


class ProductStrength(BaseModel):
    ratio: Ratio
    quantity: Quantity


class ProductIngredient(BaseModel):
    is_active: bool
    substance: ValueSetBoundCoding[CARE_SUBSTANCE_VALUSET.slug]
    strength: ProductStrength


class ProductNutrient(BaseModel):
    item: ValueSetBoundCoding[CARE_NUTRIENTS_VALUESET.slug]
    amount: ProductStrength


class DrugCharacteristic(BaseModel):
    code: DrugCharacteristicCode
    value: str


class ProductDefinitionSpec(BaseModel):
    dosage_form: ValueSetBoundCoding[MEDICATION_FORM_CODES.slug] | None
    intended_routes: list[Coding] = []
    ingredients: list[ProductIngredient] = []
    nutrients: list[ProductNutrient] = []
    drug_characteristic: list[DrugCharacteristic] = []


class BaseProductKnowledgeSpec(EMRResource):
    """Base model for healthcare service"""

    __model__ = ProductKnowledge
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    slug: str
    alternate_identifier: str | None = None
    status: ProductKnowledgeStatusOptions
    product_type: ProductTypeOptions
    code: Coding | None = None
    base_unit: ValueSetBoundCoding[CARE_UCUM_UNITS.slug]
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

    is_instance_level: bool

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.facility_id:
            mapping["is_instance_level"] = False
        else:
            mapping["is_instance_level"] = True
