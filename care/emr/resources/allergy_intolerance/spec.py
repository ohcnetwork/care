import datetime
from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.models.encounter import Encounter
from care.emr.resources.allergy_intolerance.valueset import CARE_ALLERGY_CODE_VALUESET
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class ClinicalStatusChoices(str, Enum):
    active = "active"
    inactive = "inactive"
    resolved = "resolved"


class VerificationStatusChoices(str, Enum):
    unconfirmed = "unconfirmed"
    presumed = "presumed"
    confirmed = "confirmed"
    refuted = "refuted"
    entered_in_error = "entered_in_error"


class CategoryChoices(str, Enum):
    food = "food"
    medication = "medication"
    environment = "environment"
    biologic = "biologic"


class CriticalityChoices(str, Enum):
    low = "low"
    high = "high"
    unable_to_assess = "unable_to_assess"


class AllergyIntoleranceOnSetSpec(EMRResource):
    onset_datetime: datetime.datetime = None
    onset_age: int = None
    onset_string: str = None
    note: str = None


class AllergyIntoleranceTypeOptions(str, Enum):
    allergy = "allergy"
    intolerance = "intolerance"


class BaseAllergyIntoleranceSpec(EMRResource):
    __model__ = AllergyIntolerance
    __exclude__ = ["patient", "encounter"]
    id: UUID4 = None
    encounter: UUID4
    category: CategoryChoices
    clinical_status: ClinicalStatusChoices
    verification_status: VerificationStatusChoices
    criticality: CriticalityChoices
    last_occurrence: datetime.datetime | None = None
    note: str | None = None
    allergy_intolerance_type: AllergyIntoleranceTypeOptions = (
        AllergyIntoleranceTypeOptions.allergy
    )
    recorded_date: datetime.datetime | None = None
    code: ValueSetBoundCoding[CARE_ALLERGY_CODE_VALUESET.slug]
    onset: AllergyIntoleranceOnSetSpec = {}

    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if not Encounter.objects.filter(external_id=encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return encounter


class AllergyIntoleranceUpdateSpec(BaseAllergyIntoleranceSpec):
    def perform_extra_deserialization(self, is_update, obj):
        if self.encounter:
            obj.encounter = Encounter.objects.get(external_id=self.encounter)


class AllergyIntoleranceWriteSpec(BaseAllergyIntoleranceSpec):
    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = Encounter.objects.get(external_id=self.encounter)
        obj.patient = obj.encounter.patient


class AllergyIntoleranceReadSpec(BaseAllergyIntoleranceSpec):
    """
    Validation for deeper models may not be required on read, Just an extra optimisation
    """

    # Maybe we can use model_construct() to be better at reads, need profiling to be absolutely sure
    created_by: dict = {}
    updated_by: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)
        if obj.encounter:
            mapping["encounter"] = obj.encounter.external_id
