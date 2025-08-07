from enum import Enum

from pydantic import UUID4, BaseModel, model_validator

from care.emr.models.specimen_definition import SpecimenDefinition
from care.emr.resources.base import EMRResource
from care.emr.resources.common import Coding
from care.emr.resources.specimen_definition.valueset import (
    CONTAINER_CAP_VALUESET,
    PREPARE_PATIENT_PRIOR_SPECIMEN_CODE_VALUESET,
    SPECIMEN_COLLECTION_CODE_VALUESET,
    SPECIMEN_TYPE_CODE_VALUESET,
)
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class SpecimenDefinitionStatusOptions(str, Enum):
    """Status options for specimen definition"""

    draft = "draft"
    active = "active"
    retired = "retired"


class PreferenceOptions(str, Enum):
    """Preference options for specimen type testing"""

    preferred = "preferred"
    alternate = "alternate"


class QuantitySpec(BaseModel):
    """Represents a quantity with value and unit"""

    value: float
    unit: Coding


class MinimumVolumeSpec(BaseModel):
    """Specification for minimum volume with support for quantity or string representation"""

    quantity: QuantitySpec | None = None
    string: str | None = None

    @model_validator(mode="after")
    def validate_minimum_volume(self):
        """Validates that only one minimum volume field is provided"""
        if self.quantity and self.string:
            raise ValueError("Only one of quantity or string should be provided")
        return self


class ContainerSpec(BaseModel):
    """Container specification for specimen collection"""

    description: str | None = None
    capacity: QuantitySpec | None = None
    minimum_volume: MinimumVolumeSpec | None = None
    cap: ValueSetBoundCoding[CONTAINER_CAP_VALUESET.slug] | None = None
    preparation: str | None = None


class DurationSpec(BaseModel):
    """Duration specification using value and unit"""

    value: int
    unit: Coding  # Nees to be restricted to Datetime Units


class TypeTestedSpec(BaseModel):
    """Specification for tested specimen types"""

    is_derived: bool
    preference: PreferenceOptions
    container: ContainerSpec | None = None
    requirement: str | None = None
    retention_time: DurationSpec | None = None
    single_use: bool | None = None


class BaseSpecimenDefinitionSpec(EMRResource):
    """Base model for specimen definition"""

    __model__ = SpecimenDefinition
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    slug: str
    title: str
    derived_from_uri: str | None = None
    status: SpecimenDefinitionStatusOptions
    description: str
    type_collected: ValueSetBoundCoding[SPECIMEN_TYPE_CODE_VALUESET.slug]
    patient_preparation: list[
        ValueSetBoundCoding[PREPARE_PATIENT_PRIOR_SPECIMEN_CODE_VALUESET.slug]
    ] = []
    collection: ValueSetBoundCoding[SPECIMEN_COLLECTION_CODE_VALUESET.slug] | None = (
        None
    )
    type_tested: TypeTestedSpec | None = None


class SpecimenDefinitionReadSpec(BaseSpecimenDefinitionSpec):
    """Specimen definition read specification"""

    version: int | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
