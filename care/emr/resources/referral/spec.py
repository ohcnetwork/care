from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field, field_validator, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.models.questionnaire import Questionnaire
from care.emr.models.referral import (
    Referral,
    ReferralAvailability,
    ReferralQuestionnaireResponse,
    ReferralResource,
)
from care.emr.resources.base import EMRResource
from care.emr.resources.encounter.spec import EncounterCareTeamMemberSpec
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseStatusChoices,
    QuestionnaireResponseSubmission,
)
from care.emr.resources.referral.common import (
    ReferralEntityType,
    ReferralQuestionnaireType,
    deserialize_care_team,
    serialize_care_team,
)
from care.utils.shortcuts import get_object_or_404


class ReferralStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    rejected = "rejected"


class ReferralListQuerySpec(BaseModel):
    entity_type: ReferralEntityType | None = None
    entity_id: UUID4 | None = None
    patient: UUID4 | None = None
    encounter: UUID4 | None = None

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value):
        if value == ReferralEntityType.external:
            raise ValueError("An organization or facility destination is required")
        return value

    @model_validator(mode="after")
    def validate_scope(self):
        if (self.entity_type is None) != (self.entity_id is None):
            raise ValueError("entity_type and entity_id must be supplied together")
        if not (self.entity_type or self.patient or self.encounter):
            raise ValueError("An entity, patient, or encounter scope is required")
        return self


class ReferralQuestionnaireResponseCreateSpec(EMRResource):
    __model__ = ReferralQuestionnaireResponse
    __exclude__ = ["referral", "questionnaire"]
    questionnaire: UUID4
    questionnaire_response: QuestionnaireResponseSubmission

    def perform_extra_deserialization(self, is_update, obj):
        obj.questionnaire = get_object_or_404(
            Questionnaire, external_id=self.questionnaire
        )


class ReferralQuestionnaireResponseReadSpec(ReferralQuestionnaireResponseCreateSpec):
    id: UUID4
    status: QuestionnaireResponseStatusChoices
    questionnaire_type: ReferralQuestionnaireType
    questionnaire_response: dict
    questionnaire_revision: int
    questionnaire_snapshot: dict
    created_date: datetime
    modified_date: datetime
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["questionnaire"] = obj.questionnaire.external_id
        cls.serialize_audit_users(mapping, obj)


class ReferralSpec(EMRResource):
    __model__ = Referral
    __exclude__ = [
        "availability",
        "patient",
        "encounter",
        "questionnaire",
        "questionnaire_response",
        "assignees",
        "thread",
    ]
    id: UUID4 | None = None
    title: str = Field(min_length=1, max_length=255)
    note: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if not value.strip():
            raise ValueError("Title cannot be empty")
        return value.strip()


class ReferralCreateSpec(ReferralSpec):
    availability: UUID4
    patient: UUID4 | None = None
    encounter: UUID4 | None = None
    questionnaire: UUID4
    questionnaire_response: QuestionnaireResponseSubmission

    @model_validator(mode="after")
    def validate_origin(self):
        if not self.patient and not self.encounter:
            raise ValueError("A patient or encounter is required")
        if self.encounter:
            encounter = get_object_or_404(
                Encounter.objects.select_related("patient"), external_id=self.encounter
            )
            if self.patient and self.patient != encounter.patient.external_id:
                raise ValueError("Patient does not match the encounter patient")
            self.patient = encounter.patient.external_id
        return self

    def perform_extra_deserialization(self, is_update, obj):
        for field, model in (
            ("availability", ReferralAvailability),
            ("patient", Patient),
        ):
            setattr(
                obj, field, get_object_or_404(model, external_id=getattr(self, field))
            )
        obj.encounter = (
            get_object_or_404(Encounter, external_id=self.encounter)
            if self.encounter
            else None
        )
        obj._initial_questionnaire_response = (  # noqa: SLF001
            ReferralQuestionnaireResponseCreateSpec(
                questionnaire=self.questionnaire,
                questionnaire_response=self.questionnaire_response,
            ).de_serialize()
        )


class ReferralUpdateSpec(EMRResource):
    __model__ = Referral
    __exclude__ = ["assignees"]
    title: str | MISSING = Field(default=MISSING, min_length=1, max_length=255)
    note: str | MISSING = MISSING
    status: ReferralStatus | MISSING = MISSING
    assignees: list[EncounterCareTeamMemberSpec] | MISSING = MISSING

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if not value.strip():
            raise ValueError("Title cannot be empty")
        return value.strip()

    def perform_extra_deserialization(self, is_update, obj):
        if self.assignees is not MISSING:
            obj.assignees = deserialize_care_team(self.assignees)


class ReferralAssigneesWriteSpec(BaseModel):
    members: list[EncounterCareTeamMemberSpec]


class ReferralReadSpec(ReferralSpec):
    availability: UUID4
    patient: UUID4
    patient_name: str
    availability_name: str
    status: ReferralStatus
    assignees: list[dict]
    created_date: datetime
    modified_date: datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["availability"] = obj.availability.external_id
        mapping["patient"] = obj.patient.external_id
        mapping["patient_name"] = obj.patient.name
        mapping["availability_name"] = obj.availability.name
        mapping["assignees"] = serialize_care_team(obj.assignees)


class ReferralRetrieveSpec(ReferralReadSpec):
    questionnaire_responses: list[ReferralQuestionnaireResponseReadSpec]
    encounter: UUID4 | None = None
    thread: UUID4 | None = None
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["questionnaire_responses"] = [
            ReferralQuestionnaireResponseReadSpec.serialize(response)
            for response in obj.questionnaire_responses.select_related("questionnaire")
        ]
        mapping["encounter"] = obj.encounter.external_id if obj.encounter_id else None
        mapping["thread"] = obj.thread.external_id if obj.thread_id else None
        cls.serialize_audit_users(mapping, obj)


class ReferralResourceType(str, Enum):
    diagnostic_report = "diagnostic_report"
    observation = "observation"
    condition = "condition"
    allergy_intolerance = "allergy_intolerance"
    service_request = "service_request"
    specimen = "specimen"
    questionnaire_response = "questionnaire_response"
    file_upload = "file_upload"
    immunization = "immunization"
    appointment = "appointment"
    referral = "referral"


class ReferralResourceCategory(str, Enum):
    source = "source"
    response = "response"
    metadata = "metadata"


class ReferralResourceCreateSpec(EMRResource):
    __model__ = ReferralResource
    id: UUID4 | None = None
    resource_type: ReferralResourceType
    attachment_type: ReferralResourceCategory = ReferralResourceCategory.source.value
    resource_id: UUID4
    metadata: dict = Field(default_factory=dict)


class ReferralResourceReadSpec(ReferralResourceCreateSpec):
    referral: UUID4
    created_date: datetime
    modified_date: datetime
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["referral"] = obj.referral.external_id
        cls.serialize_audit_users(mapping, obj)
