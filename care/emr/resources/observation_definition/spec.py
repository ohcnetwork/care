import enum

from pydantic import UUID4, BaseModel, field_validator, model_validator

from care.emr.models.observation_definition import ObservationDefinition
from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.resources.observation.valueset import (
    CARE_BODY_SITE_VALUESET,
    CARE_OBSERVATION_COLLECTION_METHOD,
    CARE_OBSERVATION_VALUSET,
    CARE_UCUM_UNITS,
)
from care.emr.resources.questionnaire.spec import QuestionType
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.facility.models import Facility


class ObservationCategoryChoices(str, enum.Enum):
    social_history = "social_history"
    vital_signs = "vital_signs"
    imaging = "imaging"
    laboratory = "laboratory"
    procedure = "procedure"
    survey = "survey"
    exam = "exam"
    therapy = "therapy"
    activity = "activity"


class ObservationStatusChoices(str, enum.Enum):
    draft = "draft"
    active = "active"
    retired = "retired"
    unknown = "unknown"


def validate_question_type(question_type):
    if question_type in (
        QuestionType.group.value,
        QuestionType.display.value,
        QuestionType.url.value,
    ):
        raise ValueError("Cannot create a definition with this type")
    return question_type


class ObservationDefinitionComponentSpec(BaseModel):
    code: ValueSetBoundCoding[CARE_OBSERVATION_VALUSET.slug]
    permitted_data_type: QuestionType
    permitted_unit: ValueSetBoundCoding[CARE_UCUM_UNITS.slug] | None = None

    @field_validator("permitted_data_type")
    @classmethod
    def validate_data_type(cls, permitted_data_type):
        return validate_question_type(permitted_data_type)


class BaseObservationDefinitionSpec(EMRResource):
    __model__ = ObservationDefinition
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    slug: str
    title: str
    status: ObservationStatusChoices
    description: str
    category: ObservationCategoryChoices
    code: ValueSetBoundCoding[CARE_OBSERVATION_VALUSET.slug]
    permitted_data_type: QuestionType
    component: list[ObservationDefinitionComponentSpec] = []
    body_site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None
    method: ValueSetBoundCoding[CARE_OBSERVATION_COLLECTION_METHOD.slug] | None = None
    permitted_unit: ValueSetBoundCoding[CARE_UCUM_UNITS.slug] | None = None
    derived_from_uri: str | None = None

    @field_validator("permitted_data_type")
    @classmethod
    def validate_data_type(cls, permitted_data_type):
        return validate_question_type(permitted_data_type)


class ObservationDefinitionCreateSpec(BaseObservationDefinitionSpec):
    facility: UUID4 | None = None

    @model_validator(mode="after")
    def validate_slug_uniqueness(self):
        qs = ObservationDefinition.objects.filter(slug__exact=self.slug)
        if self.facility:
            qs = qs.filter(facility__external_id=self.facility)
        if qs.exists():
            raise ValueError("Slug must be unique")
        return self

    @field_validator("facility")
    @classmethod
    def validate_facility_exists(cls, facility):
        if facility and not Facility.objects.filter(external_id=facility).exists():
            err = "Facility not found"
            raise ValueError(err)
        return facility

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility:
            obj.facility = Facility.objects.get(external_id=self.facility)


class ObservationDefinitionReadSpec(BaseObservationDefinitionSpec):
    version: int | None = None
    facility: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()
