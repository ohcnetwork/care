from enum import Enum

from pydantic import UUID4, BaseModel, field_validator

from care.emr.models.patient import PatientIdentifierConfig
from care.emr.resources.base import EMRResource
from care.emr.resources.patient_identifier.default_expression_evaluator import (
    evaluate_patient_dummy_expression,
)
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class PatientIdentifierUse(str, Enum):
    usual = "usual"
    official = "official"
    temp = "temp"
    secondary = "secondary"
    old = "old"


class PatientIdentifierStatus(str, Enum):
    draft = "draft"
    active = "active"
    inactive = "inactive"


class PatientIdentifierRetrieveConfig(BaseModel):
    retrieve_with_dob: bool = False
    retrieve_with_year_of_birth: bool = False
    retrieve_with_otp: bool = False


class IdentifierConfig(BaseModel):
    use: PatientIdentifierUse
    description: str = ""
    system: str
    required: bool
    unique: bool
    regex: str
    display: str
    retrieve_config: PatientIdentifierRetrieveConfig = {}
    default_value: str | None = None

    @field_validator("default_value")
    @classmethod
    def validate_default_value(cls, v):
        if v:
            try:
                evaluate_patient_dummy_expression(v)
            except Exception as e:
                err = "Invalid Default Value"
                raise ValueError(err) from e
        return v


class BasePatientIdentifierSpec(EMRResource):
    __model__ = PatientIdentifierConfig
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    config: IdentifierConfig
    status: PatientIdentifierStatus


class PatientIdentifierCreateSpec(BasePatientIdentifierSpec):
    facility: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            facility = get_object_or_404(Facility, external_id=self.facility)
            obj.facility = facility


class PatientIdentifierListSpec(BasePatientIdentifierSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
