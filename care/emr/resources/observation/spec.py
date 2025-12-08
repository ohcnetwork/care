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
from care.emr.resources.observation_definition.spec import BaseObservationDefinitionSpec
from care.emr.resources.questionnaire.spec import QuestionType, SubjectType
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireSubmitResultValue,
)
from care.emr.resources.user.spec import UserSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class ObservationStatus(str, Enum):
    final = "final"
    amended = "amended"
    entered_in_error = "entered_in_error"


class PerformerType(str, Enum):
    related_person = "related_person"
    user = "user"


class Performer(BaseModel):
    type: PerformerType
    id: str


class ReferenceRange(BaseModel):
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    interpretation: str
    value: str | None = None


class Component(BaseModel):
    value: QuestionnaireSubmitResultValue
    interpretation: str | None = None
    reference_range: list[ReferenceRange] = []
    code: Coding | None = None
    note: str = ""


class BaseObservationSpec(EMRResource):
    __model__ = Observation

    id: UUID4 | None = Field(None, description="Unique ID in the system")

    status: ObservationStatus = Field(
        description="Status of the observation (final or amended)"
    )

    category: Coding | None = None

    main_code: Coding | None = None

    alternate_coding: CodeableConcept | None = None

    subject_type: SubjectType = SubjectType.encounter.value

    encounter: UUID4 | None = None

    effective_datetime: datetime

    performer: Performer | None = None

    value_type: QuestionType

    value: QuestionnaireSubmitResultValue

    note: str | None = None

    body_site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None

    method: ValueSetBoundCoding[CARE_OBSERVATION_COLLECTION_METHOD.slug] | None = None

    reference_range: list[ReferenceRange] = []

    interpretation: str | None = None

    parent: UUID4 | None = None

    questionnaire_response: UUID4 | None = None

    component: list[Component] = []


class ObservationUpdateSpec(BaseObservationSpec):
    effective_datetime: datetime | None = None
    value: QuestionnaireSubmitResultValue | None = None


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
    created_by: UserSpec = {}
    updated_by: UserSpec = {}
    data_entered_by: UserSpec | None = None

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


class ObservationRetrieveSpec(ObservationReadSpec):
    observation_definition: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.observation_definition:
            mapping["observation_definition"] = BaseObservationDefinitionSpec.serialize(
                obj.observation_definition
            )
