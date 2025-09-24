import enum

from pydantic import UUID4, BaseModel, field_validator, model_validator

from care.emr.models.observation_definition import ObservationDefinition
from care.emr.resources.base import EMRResource
from care.emr.resources.common.condition_evaluator import EvaluatorConditionSpec
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.emr.resources.observation.valueset import (
    CARE_BODY_SITE_VALUESET,
    CARE_OBSERVATION_COLLECTION_METHOD,
    CARE_OBSERVATION_VALUSET,
    CARE_UCUM_UNITS,
)
from care.emr.resources.questionnaire.spec import QuestionType
from care.emr.utils.slug_type import SlugType
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


class InterpretationSpec(BaseModel):
    display: str
    icon: str | None = ""
    color: str | None = ""


class NumericRangeSpec(BaseModel):
    interpretation: InterpretationSpec
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.min is None and self.max is None:
            raise ValueError(
                "For numeric ranges, provide at least a 'min' or 'max' value (e.g., min=10 or max=20)."
            )
        return self


class ValueSetInterpretationSpec(BaseModel):
    interpretation: InterpretationSpec
    valuset: str


NORMAL_INTERPRETATION = {"display": "Normal"}
CRITICAL_INTERPRETATION = {"display": "Critical"}
ABNORMAL_INTERPRETATION = {"display": "Abnormal"}


class QualifiedRangeSpec(BaseModel):
    conditions: list[EvaluatorConditionSpec] = []
    ranges: list[NumericRangeSpec] = []
    normal_coded_value_set: str | None = ""
    critical_coded_value_set: str | None = ""
    abnormal_coded_value_set: str | None = ""
    valueset_interpretation: list[ValueSetInterpretationSpec] = []

    @model_validator(mode="after")
    def validate_categorical_or_numeric(self):
        has_ranges = bool(self.ranges)
        has_coded_values = bool(
            self.normal_coded_value_set
            or self.critical_coded_value_set
            or self.abnormal_coded_value_set
            or self.valueset_interpretation
        )

        if not has_ranges and not has_coded_values:
            raise ValueError(
                "Either 'ranges' for numeric data or coded value sets for categorical data must be provided."
            )

        if has_ranges and has_coded_values:
            raise ValueError(
                "Cannot specify both 'ranges' and coded value sets. Use ranges for numeric data or coded value sets for categorical data."
            )

        if has_ranges:
            sorted_ranges = sorted(
                self.ranges,
                key=lambda r: (r.min if r.min is not None else float("-inf")),
            )
            for i in range(1, len(sorted_ranges)):
                prev = sorted_ranges[i - 1]
                curr = sorted_ranges[i]
                prev_max = prev.max if prev.max is not None else float("inf")
                curr_min = curr.min if curr.min is not None else float("-inf")
                if curr_min < prev_max:
                    raise ValueError(
                        "Overlapping ranges detected between min-max values in the ranges array."
                    )

        if has_coded_values:
            slugs = [
                interpretation.valuset
                for interpretation in self.valueset_interpretation
            ]
            if self.abnormal_coded_value_set:
                slugs.append(self.abnormal_coded_value_set)
            if self.critical_coded_value_set:
                slugs.append(self.critical_coded_value_set)
            if self.normal_coded_value_set:
                slugs.append(self.normal_coded_value_set)
            if len(slugs) != len(set(slugs)):
                raise ValueError("Duplicate valueset interpretations detected")

        return self


class ObservationDefinitionComponentSpec(BaseModel):
    code: ValueSetBoundCoding[CARE_OBSERVATION_VALUSET.slug]
    permitted_data_type: QuestionType
    permitted_unit: ValueSetBoundCoding[CARE_UCUM_UNITS.slug] | None = None
    qualified_ranges: list[QualifiedRangeSpec] = []

    @field_validator("permitted_data_type")
    @classmethod
    def validate_data_type(cls, permitted_data_type):
        return validate_question_type(permitted_data_type)


class BaseObservationDefinitionSpec(EMRResource):
    __model__ = ObservationDefinition
    __exclude__ = ["facility"]

    id: UUID4 | None = None
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
    qualified_ranges: list[QualifiedRangeSpec] = []

    @field_validator("permitted_data_type")
    @classmethod
    def validate_data_type(cls, permitted_data_type):
        return validate_question_type(permitted_data_type)

    @model_validator(mode="after")
    def validate_qualified_ranges_consistency(self):
        if not self.qualified_ranges:
            return self

        first_spec = self.qualified_ranges[0]
        uses_ranges = bool(first_spec.ranges)

        for spec in self.qualified_ranges:
            if bool(spec.ranges) != uses_ranges:
                raise ValueError(
                    "All qualified ranges must use the same data type (either all numeric ranges or all coded value sets)"
                )
        return self


class ObservationDefinitionCreateSpec(BaseObservationDefinitionSpec):
    facility: UUID4 | None = None
    slug_value: SlugType

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
        obj.slug = self.slug_value


class ObservationDefinitionUpdateSpec(BaseObservationDefinitionSpec):
    slug_value: SlugType

    def perform_extra_deserialization(self, is_update, obj):
        obj.slug = self.slug_value


class ObservationDefinitionReadSpec(BaseObservationDefinitionSpec):
    version: int | None = None
    facility: dict | None = None

    slug_config: dict
    slug: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()
        mapping["slug_config"] = obj.parse_slug(obj.slug)
