import datetime
from enum import Enum

from pydantic import UUID4, Field, field_validator

from care.emr.fhir.schema.base import Coding
from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.models.encounter import Encounter
from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.allergy_intolerance.valueset import CARE_ALLERGY_CODE_VALUESET
from care.emr.resources.base import EMRResource
from care.emr.resources.user.spec import UserSpec


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
    note: str


class BaseAllergyIntoleranceSpec(EMRResource):
    __model__ = AllergyIntolerance
    __exclude__ = ["patient", "encounter"]
    id: UUID4 = None


class AllergyIntoleranceUpdateSpec(BaseAllergyIntoleranceSpec):
    clinical_status: ClinicalStatusChoices
    verification_status: VerificationStatusChoices
    criticality: CriticalityChoices
    last_occurrence: datetime.datetime | None = None
    note: str | None = None
    encounter: UUID4

    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if not Encounter.objects.filter(external_id=encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return encounter

    def perform_extra_deserialization(self, is_update, obj):
        if self.encounter:
            obj.encounter = Encounter.objects.get(external_id=self.encounter)


class AllergyIntoleranceWriteSpec(BaseAllergyIntoleranceSpec):
    clinical_status: ClinicalStatusChoices
    verification_status: VerificationStatusChoices
    category: CategoryChoices
    criticality: CriticalityChoices
    last_occurrence: datetime.datetime | None = None
    recorded_date: datetime.datetime | None = None
    encounter: UUID4
    code: Coding = Field(
        {}, json_schema_extra={"slug": CARE_ALLERGY_CODE_VALUESET.slug}
    )
    onset: AllergyIntoleranceOnSetSpec = {}

    @field_validator("code")
    @classmethod
    def validate_code(cls, code: int):
        return validate_valueset(
            "code", cls.model_fields["code"].json_schema_extra["slug"], code
        )

    @field_validator("encounter")
    @classmethod
    def validate_encounter_exists(cls, encounter):
        if not Encounter.objects.filter(external_id=encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return encounter

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = Encounter.objects.get(external_id=self.encounter)
        obj.patient = obj.encounter.patient


class AllergyIntoleranceReadSpec(BaseAllergyIntoleranceSpec):
    """
    Validation for deeper models may not be required on read, Just an extra optimisation
    """

    # Maybe we can use model_construct() to be better at reads, need profiling to be absolutely sure
    clinical_status: str
    verification_status: str
    category: str
    criticality: str
    code: Coding
    encounter: UUID4
    onset: AllergyIntoleranceOnSetSpec = dict
    last_occurrence: datetime.datetime | None = None
    recorded_date: datetime.datetime | None = None
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
