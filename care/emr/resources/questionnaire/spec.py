import hashlib
import json
import uuid
from enum import Enum
from typing import Any

from pydantic import (
    UUID4,
    UUID5,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from care.emr.models import Questionnaire, ValueSet
from care.emr.models.organization import FacilityOrganization
from care.emr.resources.base import EMRResource
from care.emr.resources.observation.valueset import (
    CARE_OBSERVATION_VALUSET,
    CARE_UCUM_UNITS,
)
from care.emr.utils.slug_type import SlugType
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class QuestionnaireAuthContext(str, Enum):
    instance = "instance"
    facility_organization = "facility_organization"
    facility = "facility"
    user = "user"


class EnableOperator(str, Enum):
    exists = "exists"
    equals = "equals"
    not_equals = "not_equals"
    greater = "greater"
    less = "less"
    greater_or_equals = "greater_or_equals"
    less_or_equals = "less_or_equals"


class EnableBehavior(str, Enum):
    all = "all"
    any = "any"


class DisabledDisplay(str, Enum):
    hidden = "hidden"
    protected = "protected"


class QuestionType(str, Enum):
    group = "group"
    boolean = "boolean"
    decimal = "decimal"
    integer = "integer"
    string = "string"
    text = "text"
    display = "display"
    date = "date"
    datetime = "dateTime"
    time = "time"
    choice = "choice"
    # open_choice = "open_choice"
    url = "url"
    # attachment = "attachment"
    # reference = "reference"
    quantity = "quantity"
    structured = "structured"


class AnswerConstraint(str, Enum):
    required = "required"
    optional = "optional"


class QuestionnaireStatus(str, Enum):
    active = "active"
    retired = "retired"
    draft = "draft"


class SubjectType(str, Enum):
    patient = "patient"
    encounter = "encounter"
    location = "location"
    device = "device"
    facility = "facility"


class QuestionnaireBaseSpec(EMRResource):
    __model__ = Questionnaire


class Performer(QuestionnaireBaseSpec):
    performer_type: str = Field(description="Type of performer from FHIR specification")
    performer_id: str | None = Field(description="ID of the reference")
    text: str | None = Field(
        description="Text description when no hard reference exists"
    )


class EnableWhen(QuestionnaireBaseSpec):
    question: str = Field(description="Link ID of the question to check against")
    operator: EnableOperator
    answer: Any = Field(description="Value for operator, based on question type")


class AnswerOption(QuestionnaireBaseSpec):
    value: Any = Field(description="Value based on question type")
    initial_selected: bool = Field(
        default=False,
        description="Whether option is initially selected",
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str, info):
        if not value.strip():
            raise ValueError(
                "All the answer option values must be provided for custom choices"
            )
        return value.strip()


class TemplateConfig(QuestionnaireBaseSpec):
    name: str
    content: str
    structured_content: dict | None = None
    meta: dict | None = None


class ValueSetConfig(BaseModel):
    slug: SlugType | None = None
    external_id: UUID4 | None = None

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.slug and not self.external_id:
            raise ValueError("Either one of slug or external_id must be provided")
        return self


class Question(QuestionnaireBaseSpec):
    model_config = ConfigDict(populate_by_name=True)

    link_id: str = Field(description="Unique human readable ID for linking")
    id: UUID4 | UUID5 = Field(description="Unique machine provided UUID")
    code: ValueSetBoundCoding[CARE_OBSERVATION_VALUSET.slug] | None = None
    collect_time: bool = Field(
        default=False, description="Whether to collect timestamp"
    )
    collect_performer: bool = Field(
        default=False,
        description="Whether to collect performer",
    )
    text: str = Field(description="Question text")
    description: str | None = Field(None, description="Question description")
    type: QuestionType
    structured_type: str | None = None  # TODO : Add validation later
    enable_when: list[EnableWhen] | None = None
    enable_behavior: EnableBehavior | None = None
    disabled_display: DisabledDisplay | None = None
    collect_body_site: bool | None = None
    collect_method: bool | None = None
    required: bool | None = None
    repeats: bool | None = None
    read_only: bool | None = None
    max_length: int | None = None
    answer_constraint: AnswerConstraint | None = None
    answer_option: list[AnswerOption] | None = None
    answer_value_set: ValueSetConfig | None = None
    is_observation: bool | None = None
    unit: ValueSetBoundCoding[CARE_UCUM_UNITS.slug] | None = None
    questions: list["Question"] = []
    formula: str | None = None
    styling_metadata: dict = {}
    templates: list[TemplateConfig] = []
    is_component: bool = False

    @field_validator("answer_value_set")
    @classmethod
    def validate_value_set(cls, valueset):
        if valueset is None:
            return valueset

        err = "Value set not found"
        if valueset.external_id:
            if not ValueSet.objects.filter(external_id=valueset.external_id).exists():
                raise ValueError(err)
            return valueset

        if not ValueSet.objects.filter(
            slug=valueset.slug,
            auth_context=QuestionnaireAuthContext.instance,
        ).exists():
            raise ValueError(err)
        return valueset

    def get_all_ids(self):
        ids = []
        for question in self.questions:
            ids.append({"id": question.id, "link_id": question.link_id})
            if question.questions:
                ids.extend(question.get_all_ids())
        return ids

    @model_validator(mode="after")
    def validate_choice_and_group_questions(self):
        if self.type in [QuestionType.choice, QuestionType.quantity] and not (
            self.answer_option or self.answer_value_set
        ):
            raise ValueError(
                "Either answer options or a value set must be provided for choice type questions"
            )

        if self.type == QuestionType.group and not self.questions:
            raise ValueError("Group type questions must have at least one sub-question")

        return self


class QuestionnaireWriteSpec(QuestionnaireBaseSpec):
    version: str = Field("1.0", frozen=True, description="Version of the questionnaire")
    slug: SlugType | None = None

    title: str
    description: str | None = None

    status: QuestionnaireStatus
    styling_metadata: dict = Field(
        {}, description="Styling requirements without validation"
    )
    questions: list[Question]

    @field_validator("slug")
    @classmethod
    def check_internal_slug_conflict(cls, slug: str, info):
        from care.emr.registries.system_questionnaire.system_questionnaire import (
            InternalQuestionnaireRegistry,
        )

        if InternalQuestionnaireRegistry.check_type_exists(slug):
            err = "Slug cannot shadow internal question types"
            raise ValueError(err)
        return slug

    @field_validator("title")
    @classmethod
    def validate_title(cls, title: str, info):
        if not title.strip():
            raise ValueError("Title cannot be empty")
        return title.strip()

    def get_all_ids(self):
        ids = []
        for question in self.questions:
            ids.append({"id": question.id, "link_id": question.link_id})
            if question.questions:
                ids.extend(question.get_all_ids())
        return ids

    @model_validator(mode="after")
    def validate_unique_id(self):
        # Get all link and question id's and check for uniqueness
        ids = self.get_all_ids()
        link_ids = [id["link_id"] for id in ids]
        if len(link_ids) != len(set(link_ids)):
            err = "Link IDs must be unique"
            raise ValueError(err)
        ids = [id["id"] for id in ids]
        if len(ids) != len(set(ids)):
            err = "Question IDs must be unique"
            raise ValueError(err)
        return self


class QuestionnaireCreateSpec(QuestionnaireWriteSpec):
    auth_context: QuestionnaireAuthContext
    facility: UUID4 | None = None
    facility_organization: UUID4 | None = None
    subject_type: SubjectType

    def perform_extra_deserialization(self, is_update, obj):
        if obj.auth_context in (
            QuestionnaireAuthContext.facility,
            QuestionnaireAuthContext.user,
        ):
            obj.facility = get_object_or_404(
                Facility.objects.only("id"), external_id=self.facility
            )
        if obj.auth_context == QuestionnaireAuthContext.facility_organization:
            obj.facility_organization = get_object_or_404(
                FacilityOrganization, external_id=self.facility_organization
            )
            obj.facility = obj.facility_organization.facility
            obj.internal_organization_cache = [
                *obj.facility_organization.parent_cache,
                obj.facility_organization.id,
            ]
        current_obj_questions = json.dumps(obj.questions, sort_keys=True).encode(
            "utf-8"
        )
        obj.questions_hash = hashlib.sha256(current_obj_questions).hexdigest()

    @field_validator("facility")
    @classmethod
    def validate_facility(cls, facility: UUID4, info):
        if facility and not Facility.objects.filter(external_id=facility).exists():
            err = "Facility not found"
            raise ValueError(err)
        return facility

    @field_validator("facility_organization")
    @classmethod
    def validate_facility_organization(cls, facility_organization: UUID4, info):
        if (
            facility_organization
            and not FacilityOrganization.objects.filter(
                external_id=facility_organization
            ).exists()
        ):
            err = "Facility organization not found"
            raise ValueError(err)
        return facility_organization

    @model_validator(mode="after")
    def validate_keys(self):
        if (
            self.subject_type == SubjectType.patient
            and self.auth_context != QuestionnaireAuthContext.instance
        ):
            raise ValueError(
                "Patient questionnaires are only supported at the instance level"
            )
        if self.auth_context == QuestionnaireAuthContext.user and not self.facility:
            raise ValueError("Facility is required")
        if self.auth_context == QuestionnaireAuthContext.facility and not self.facility:
            raise ValueError("Facility is required")
        if (
            self.auth_context == QuestionnaireAuthContext.facility_organization
            and not self.facility_organization
        ):
            raise ValueError("Facility organization is required")
        return self

    # @model_validator(mode="after")
    # def validate_slug(self, info):
    #     # Uniqueness changes based on the auth context
    #     if self.auth_context == QuestionnaireAuthContext.instance:
    #         queryset = Questionnaire.objects.filter(slug=self.slug)
    #     elif self.auth_context == QuestionnaireAuthContext.facility:
    #         queryset = Questionnaire.objects.filter(facility__external_id=self.facility)
    #     elif self.auth_context == QuestionnaireAuthContext.facility_organization:
    #         queryset = Questionnaire.objects.filter(
    #             facility_organization__organization__external_id=self.facility_organization
    #         )
    #     elif self.auth_context == QuestionnaireAuthContext.user:
    #         queryset = Questionnaire.objects.filter(
    #             created_by=self.get_serializer_context(info)["user"]
    #         )
    #     else:
    #         raise ValueError("Invalid auth context")
    #     if queryset.exists():
    #         err = "Slug must be unique"
    #         raise ValueError(err)

    #     return self


class QuestionnaireSpec(QuestionnaireWriteSpec):
    pass


class QuestionnaireUpdateSpec(QuestionnaireWriteSpec):
    # @field_validator("slug")
    # @classmethod
    # def validate_slug(cls, slug: str, info):
    #     # Uniqueness changes based on the auth context
    #     current_object = info.context["object"]
    #     queryset = Questionnaire.objects.exclude(
    #         Q(id=info.context["object"].id) | Q(latest_revision__isnull=False)
    #     )
    #     if current_object.auth_context == QuestionnaireAuthContext.instance:
    #         queryset = queryset.filter(slug=slug)
    #     elif current_object.auth_context == QuestionnaireAuthContext.facility:
    #         queryset = queryset.filter(facility=current_object.facility)
    #     elif (
    #         current_object.auth_context
    #         == QuestionnaireAuthContext.facility_organization
    #     ):
    #         queryset = queryset.filter(
    #             facility_organization=current_object.facility_organization
    #         )
    #     elif current_object.auth_context == QuestionnaireAuthContext.user:
    #         queryset = queryset.filter(created_by=info.context["user"])
    #     else:
    #         raise ValueError("Invalid auth context")
    #     if queryset.exists():
    #         err = "Slug must be unique"
    #         raise ValueError(err)
    #     return slug

    def perform_extra_deserialization(self, is_update, obj):
        old_obj_hash = (
            Questionnaire.objects.only("questions_hash").get(id=obj.id).questions_hash
        )
        current_obj_questions = json.dumps(obj.questions, sort_keys=True).encode(
            "utf-8"
        )
        current_obj_hash = hashlib.sha256(current_obj_questions).hexdigest()
        if old_obj_hash != current_obj_hash:
            old_obj = Questionnaire.objects.get(id=obj.id)
            old_obj.id = None
            old_obj.external_id = uuid.uuid4()
            old_obj.latest_revision = obj
            old_obj.save()
            obj.internal_revision += 1
            obj.questions_hash = current_obj_hash
        return obj


class QuestionnaireReadSpec(QuestionnaireBaseSpec):
    id: str
    slug: SlugType | None = None
    version: str
    title: str
    description: str | None = None
    status: QuestionnaireStatus
    subject_type: SubjectType
    styling_metadata: dict
    questions: list
    created_by: dict | None = None
    updated_by: dict | None = None
    internal_revision: int

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)


# Add this to handle recursive Question type
Question.model_rebuild()
