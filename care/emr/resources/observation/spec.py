from datetime import datetime
from enum import Enum
from typing import ClassVar, Literal

from pydantic import UUID4, AwareDatetime, BaseModel, ConfigDict, Field

from care.emr.models.encounter import Encounter
from care.emr.models.observation import Observation
from care.emr.resources.base import EMRResource, model_from_cache
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
from care.utils.shortcuts import get_object_or_404


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
    interpretation: str | dict = {}
    reference_range: list[ReferenceRange] = []
    code: Coding | None = None
    note: str = ""


class BaseObservationSpec(EMRResource):
    __model__ = Observation

    id: UUID4 | None = Field(None, description="Unique ID in the system")

    status: ObservationStatus = Field(
        description="Status of the observation (final, amended or entered in error)"
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

    interpretation: dict = {}

    parent: UUID4 | None = None

    questionnaire_response: UUID4 | None = None

    component: list[Component] = []


class ObservationCreateSpec(EMRResource):
    """An observation entered independently of a questionnaire or diagnostic report."""

    __model__ = Observation
    model_config = ConfigDict(extra="forbid")
    meta: ClassVar[dict] = {}

    encounter: UUID4
    status: Literal[ObservationStatus.final] = ObservationStatus.final
    main_code: Coding
    effective_datetime: AwareDatetime
    value_type: QuestionType
    value: QuestionnaireSubmitResultValue
    category: Coding | None = None
    alternate_coding: CodeableConcept | None = None
    performer: Performer | None = None
    note: str | None = None
    body_site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None
    method: ValueSetBoundCoding[CARE_OBSERVATION_COLLECTION_METHOD.slug] | None = None
    component: list[Component] = []

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = get_object_or_404(Encounter, external_id=self.encounter)
        obj.patient = obj.encounter.patient
        obj.subject_type = SubjectType.encounter.value
        obj.subject_id = obj.encounter.external_id
        obj.status = self.status.value


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
    is_random: bool = Field(
        description="Whether the observation was entered independently of a questionnaire or diagnostic report"
    )
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
        mapping["is_random"] = obj.is_random

        cls.serialize_audit_users(mapping, obj)
        if obj.data_entered_by:
            mapping["data_entered_by"] = model_from_cache(
                UserSpec, id=obj.data_entered_by_id
            )


class ObservationRetrieveSpec(ObservationReadSpec):
    observation_definition: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.observation_definition:
            mapping["observation_definition"] = BaseObservationDefinitionSpec.serialize(
                obj.observation_definition
            )
