from datetime import datetime

from pydantic import UUID4, UUID5, BaseModel

from care.emr.models.questionnaire import QuestionnaireResponse
from care.emr.resources.base import EMRResource
from care.emr.resources.common import Coding
from care.emr.resources.questionnaire.spec import QuestionnaireReadSpec
from care.emr.resources.user.spec import UserSpec


class QuestionnaireSubmitResultValue(BaseModel):
    value: str | None = None
    # For Quantity
    unit: Coding | None = None
    # For Codes
    coding: Coding | None = None


class QuestionnaireSubmitResult(BaseModel):
    question_id: UUID4 | UUID5
    body_site: Coding | None = None
    method: Coding | None = None
    taken_at: datetime | None = None
    values: list[QuestionnaireSubmitResultValue] = []
    note: str | None = None
    sub_results: list[list["QuestionnaireSubmitResult"]] = []


class QuestionnaireSubmitRequest(BaseModel):
    resource_id: UUID4
    encounter: UUID4 | None = None
    patient: UUID4
    results: list[QuestionnaireSubmitResult]


class QuestionnaireResponseReadSpec(EMRResource):
    __model__ = QuestionnaireResponse

    id: UUID4
    questionnaire: QuestionnaireReadSpec
    subject_id: str
    responses: list
    encounter: str | None = None
    structured_responses: dict
    structured_response_type: str
    created_by: UserSpec = dict
    updated_by: UserSpec = dict
    created_date: datetime | None = None
    modified_date: datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.questionnaire:
            mapping["questionnaire"] = QuestionnaireReadSpec.serialize(
                obj.questionnaire
            )
        if obj.encounter:
            mapping["encounter"] = obj.encounter.external_id
        else:
            mapping["encounter"] = None
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)
