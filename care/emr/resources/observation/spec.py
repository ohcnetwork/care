from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field

from care.emr.models.observation import Observation
from care.emr.resources.base import EMRResource
from care.emr.resources.common import Coding
from care.emr.resources.common.codable_concept import CodeableConcept
from care.emr.resources.observation.valueset import (
    CARE_BODY_SITE_VALUESET,
    CARE_OBSERVATION_COLLECTION_METHOD,
)
from care.emr.resources.questionnaire.spec import QuestionType, SubjectType
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireSubmitResultValue,
)
from care.emr.resources.user.spec import UserSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class ObservationStatus(str, Enum):
    final = "final"
    amended = "amended"


class PerformerType(str, Enum):
    related_person = "related_person"
    user = "user"


class Performer(BaseModel):
    type: PerformerType
    id: str


class ReferenceRange(BaseModel):
    low: float | None = None
    high: float | None = None
    unit: str | None = None
    text: str | None = None


class Component(BaseModel):
    value: QuestionnaireSubmitResultValue
    interpretation: str | None = None
    reference_range: list[ReferenceRange] = []
    code: Coding | None = None
    note: str = ""


class BaseObservationSpec(EMRResource):
    __model__ = Observation

    id: str = Field("", description="Unique ID in the system")

    status: ObservationStatus = Field(
        description="Status of the observation (final or amended)"
    )

    category: Coding | None = Field(
        None, description="List of codeable concepts derived from the questionnaire"
    )

    main_code: Coding | None = Field(
        None, description="Code for the observation (LOINC binding)"
    )

    alternate_coding: CodeableConcept = dict

    subject_type: SubjectType

    encounter: UUID4 | None = None

    effective_datetime: datetime = Field(
        ...,
        description="Datetime when observation was recorded",
    )

    performer: Performer | None = Field(
        None,
        description="Who performed the observation (currently supports RelatedPerson)",
    )  # If none the observation is captured by the data entering person

    value_type: QuestionType = Field(
        description="Type of value",
    )

    value: QuestionnaireSubmitResultValue = Field(
        description="Value of the observation if not code. For codes, contains display text",
    )

    note: str | None = Field(None, description="Additional notes about the observation")

    body_site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None

    method: ValueSetBoundCoding[CARE_OBSERVATION_COLLECTION_METHOD.slug] | None = None

    reference_range: list[ReferenceRange] = Field(
        [], description="Reference ranges for interpretation"
    )

    interpretation: str | None = Field(
        None, description="Interpretation based on the reference range"
    )

    parent: UUID4 | None = Field(None, description="ID reference to parent observation")

    questionnaire_response: UUID4 | None = None

    component: list[Component] = []


class ObservationSpec(BaseObservationSpec):
    data_entered_by_id: int
    created_by_id: int
    updated_by_id: int

    def perform_extra_deserialization(self, is_update, obj):
        obj.external_id = self.id
        obj.data_entered_by_id = self.data_entered_by_id
        obj.created_by_id = self.created_by_id
        obj.updated_by_id = self.updated_by_id

        self.meta.pop("data_entered_by_id", None)
        if not is_update:
            obj.id = None


class ObservationReadSpec(BaseObservationSpec):
    created_by: UserSpec = dict
    updated_by: UserSpec = dict
    data_entered_by: UserSpec = dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        # Avoiding extra queries
        mapping["encounter"] = None
        mapping["patient"] = None
        mapping["questionnaire_response"] = None

        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)
        if obj.data_entered_by:
            mapping["data_entered_by"] = UserSpec.serialize(obj.data_entered_by)
