import uuid
from enum import Enum
from typing import Any

from pydantic import UUID4, ConfigDict, Field, field_validator, model_validator

from care.emr.fhir.schema.base import Coding
from care.emr.models import Questionnaire, QuestionnaireTag, ValueSet
from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.base import EMRResource
from care.emr.resources.observation.valueset import (
    CARE_OBSERVATION_VALUSET,
    CARE_UCUM_UNITS,
)
from care.emr.resources.user.spec import UserSpec


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


class Question(QuestionnaireBaseSpec):
    model_config = ConfigDict(populate_by_name=True)

    link_id: str = Field(description="Unique human readable ID for linking")
    id: UUID4 = Field(
        description="Unique machine provided UUID", default_factory=uuid.uuid4
    )
    code: Coding | None = Field(
        None,
        description="Coding for observation creation",
        json_schema_extra={"slug": CARE_OBSERVATION_VALUSET.slug},
    )
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
    answer_constraint: AnswerConstraint | None = Field(
        alias="answerConstraint", default=None
    )
    answer_option: list[AnswerOption] | None = None
    answer_value_set: str | None = None
    is_observation: bool | None = None
    unit: Coding | None = Field(None, json_schema_extra={"slug": CARE_UCUM_UNITS.slug})
    questions: list["Question"] = []
    formula: str | None = None
    styling_metadata: dict = {}

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, code):
        return validate_valueset(
            "unit", cls.model_fields["unit"].json_schema_extra["slug"], code
        )

    @field_validator("answer_value_set")
    @classmethod
    def validate_value_set(cls, slug):
        if not ValueSet.objects.filter(slug=slug).exists():
            err = "Value set not found"
            raise ValueError(err)
        return slug

    def get_all_ids(self):
        ids = []
        for question in self.questions:
            ids.append({"id": question.id, "link_id": question.link_id})
            if question.questions:
                ids.extend(question.get_all_ids())
        return ids

    @model_validator(mode="after")
    def validate_value_set_or_options(self):
        if self.type in [QuestionType.choice, QuestionType.quantity] and not (
            self.answer_option or self.answer_value_set
        ):
            err = "Either answer options or a value set must be provided for choice type questions"
            raise ValueError(err)
        return self

    @model_validator(mode="after")
    def validate_group_does_not_repeat(self):
        if self.type == QuestionType.group and self.repeats:
            err = "Group type questions cannot be repeated"
            raise ValueError(err)
        return self


class QuestionnaireWriteSpec(QuestionnaireBaseSpec):
    version: str = Field("1.0", frozen=True, description="Version of the questionnaire")
    slug: str | None = Field(None, min_length=5, max_length=25, pattern=r"^[-\w]+$")
    title: str
    description: str = ""
    type: str = "custom"
    status: QuestionnaireStatus
    subject_type: SubjectType
    styling_metadata: dict = Field(
        {}, description="Styling requirements without validation"
    )
    questions: list[Question]

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, slug: str, info):
        queryset = Questionnaire.objects.filter(slug=slug)
        context = cls.get_serializer_context(info)
        if context.get("is_update", False):
            queryset = queryset.exclude(id=info.context["object"].id)
        if queryset.exists():
            err = "Slug must be unique"
            raise ValueError(err)
        from care.emr.registries.system_questionnaire.system_questionnaire import (
            InternalQuestionnaireRegistry,
        )

        if InternalQuestionnaireRegistry.check_type_exists(slug):
            err = "Slug cannot shadow internal question types"
            raise ValueError(err)
        return slug

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


class QuestionnaireSpec(QuestionnaireWriteSpec):
    organizations: list[UUID4] = Field(min_length=1)

    def perform_extra_deserialization(self, is_update, obj):
        obj._organizations = self.organizations  # noqa SLF001


class QuestionnaireUpdateSpec(QuestionnaireWriteSpec):
    pass


class QuestionnaireReadSpec(QuestionnaireBaseSpec):
    id: str
    slug: str | None = None
    version: str
    title: str
    description: str = ""
    status: QuestionnaireStatus
    subject_type: SubjectType
    styling_metadata: dict
    questions: list
    created_by: UserSpec = dict
    updated_by: UserSpec = dict
    tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        tags = []
        for tag in obj.tags:
            tags.append(QuestionnaireTag.get_tag(tag))
        mapping["tags"] = tags
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)


# Add this to handle recursive Question type
Question.model_rebuild()


class QuestionnaireTagSpec(EMRResource):
    __model__ = QuestionnaireTag
    id: UUID4 | None = None
    name: str
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, slug: str, info):
        queryset = QuestionnaireTag.objects.filter(slug=slug)
        context = cls.get_serializer_context(info)
        if context.get("is_update", False):
            queryset = queryset.exclude(id=info.context["object"].id)
        if queryset.exists():
            err = "Slug must be unique"
            raise ValueError(err)
        return slug

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
