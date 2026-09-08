from datetime import datetime

from pydantic import UUID4, UUID5, BaseModel

from care.emr.models.facility_resource import FacilityResourceQuestionnaireResponse
from care.emr.resources.base import EMRResource
from care.emr.resources.common import Coding
from care.emr.resources.questionnaire.spec import QuestionnaireReadSpec
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseStatusChoices,
    QuestionnaireSubmitResult,
    QuestionnaireSubmitResultValue,
)
from care.emr.resources.user.spec import UserSpec


class ResourceQuestionnaireSubmitResult(BaseModel):
    question_id: UUID4 | UUID5
    method: Coding | None = None
    taken_at: datetime | None = None
    values: list[QuestionnaireSubmitResultValue] = []
    note: str | None = None
    sub_results: list[list["ResourceQuestionnaireSubmitResult"]] = []


class ResourceQuestionnaireSubmitRequest(BaseModel):
    resource_id: UUID4
    results: list[QuestionnaireSubmitResult]


class EMRResourceQuestionnaireResponseBase(EMRResource):
    __model__ = FacilityResourceQuestionnaireResponse


class ResourceQuestionnaireResponseUpdate(EMRResourceQuestionnaireResponseBase):
    status: QuestionnaireResponseStatusChoices = (
        QuestionnaireResponseStatusChoices.completed.value
    )


class ResourceQuestionnaireResponseReadSpec(EMRResourceQuestionnaireResponseBase):
    id: UUID4
    status: str
    questionnaire: QuestionnaireReadSpec
    questionnaire_latest_revision_id: UUID4 | None = None
    subject_id: str
    responses: list
    cleaned_response: dict
    structured_responses: dict
    structured_response_type: str
    created_by: UserSpec = dict
    updated_by: UserSpec = dict
    created_date: datetime | None = None
    modified_date: datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        questionnaire = obj.resolved_questionnaire
        if questionnaire:
            mapping["questionnaire"] = QuestionnaireReadSpec.serialize(questionnaire)
            mapping["questionnaire_latest_revision_id"] = obj.questionnaire.external_id
        cls.serialize_audit_users(mapping, obj)
