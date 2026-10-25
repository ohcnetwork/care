from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    UUID4,
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)
from pydantic.experimental.missing_sentinel import MISSING
from rest_framework.exceptions import ValidationError

from care.emr.models.organization import FacilityOrganization, Organization
from care.emr.models.questionnaire import Questionnaire
from care.emr.models.referral import (
    ReferralAvailability,
    ReferralAvailabilityQuestionnaire,
)
from care.emr.resources.base import EMRResource
from care.emr.resources.encounter.spec import EncounterCareTeamMemberSpec
from care.emr.resources.questionnaire.spec import SubjectType
from care.emr.resources.referral.common import (
    ReferralAvailabilityStatus,
    ReferralEntityType,
    ReferralQuestionnaireType,
    ReferralType,
    deserialize_care_team,
    serialize_care_team,
)
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


def resolve_questionnaires(identifiers):
    questionnaires = list(
        Questionnaire.objects.filter(
            external_id__in=identifiers,
            latest_revision__isnull=True,
            status="active",
            subject_type__in=[SubjectType.patient.value, SubjectType.encounter.value],
        )
    )
    if len(questionnaires) != len(set(identifiers)):
        raise ValidationError("Active questionnaire not found")
    return questionnaires


class ReferralAvailabilityQuestionnaireSpec(BaseModel):
    questionnaire: UUID4
    questionnaire_type: ReferralQuestionnaireType = (
        ReferralQuestionnaireType.request.value
    )


def normalize_questionnaire_mappings(value):
    if not isinstance(value, list):
        return value
    return [
        {"questionnaire": entry} if isinstance(entry, (str, UUID)) else entry
        for entry in value
    ]


ReferralQuestionnaireMappings = Annotated[
    list[ReferralAvailabilityQuestionnaireSpec],
    BeforeValidator(normalize_questionnaire_mappings),
]


def assign_questionnaire_mappings(availability, mappings):
    questionnaire_types = {
        mapping.questionnaire: mapping.model_dump(mode="json")["questionnaire_type"]
        for mapping in mappings
    }
    if len(questionnaire_types) != len(mappings):
        raise ValidationError("Each questionnaire can only be mapped once")
    questionnaires = resolve_questionnaires(questionnaire_types)
    availability._questionnaires = questionnaires  # noqa: SLF001
    availability._questionnaire_types = {  # noqa: SLF001
        questionnaire.id: questionnaire_types[questionnaire.external_id]
        for questionnaire in questionnaires
    }


def validate_internal_organization_facility(availability):
    if (
        availability.entity_type == ReferralEntityType.internal_organization
        and availability.facility_id is not None
        and availability.internal_organization.facility_id != availability.facility_id
    ):
        raise ValidationError(
            "Facility must match the internal organization's facility"
        )


class ReferralAvailabilityQuerySpec(BaseModel):
    entity_type: ReferralEntityType


class ReferralAvailabilityConfigQuerySpec(ReferralAvailabilityQuerySpec):
    entity_id: UUID4

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value):
        if value == ReferralEntityType.external:
            raise ValueError("An organization or facility destination is required")
        return value


class ReferralAvailabilitySpec(EMRResource):
    __model__ = ReferralAvailability
    __exclude__ = [
        "external_organization",
        "internal_organization",
        "facility",
        "care_team",
        "questionnaires",
    ]
    id: UUID4 | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    status: ReferralAvailabilityStatus
    is_public: bool = False
    referral_type: ReferralType

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be empty")
        return value.strip()


class ReferralAvailabilityCreateSpec(ReferralAvailabilitySpec):
    entity_type: ReferralEntityType
    external_organization: UUID4 | None = None
    internal_organization: UUID4 | None = None
    facility: UUID4 | None = None
    external_entity: dict = Field(default_factory=dict)
    care_team: list[EncounterCareTeamMemberSpec] = Field(default_factory=list)
    questionnaires: ReferralQuestionnaireMappings = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_destination(self):
        targets = {
            "external_organization": self.external_organization,
            "internal_organization": self.internal_organization,
            "facility": self.facility,
        }
        provided = [target for target, value in targets.items() if value is not None]
        if self.entity_type == ReferralEntityType.internal_organization:
            provided = [target for target in provided if target != "facility"]
        expected = (
            []
            if self.entity_type == ReferralEntityType.external
            else [self.entity_type.value]
        )
        if provided != expected:
            raise ValidationError(
                "Exactly the destination matching entity_type is required"
            )
        if self.entity_type == ReferralEntityType.external:
            raise ValidationError("External Entity creation is not allowed via API")
        return self

    def perform_extra_deserialization(self, is_update, obj):
        targets = {
            "external_organization": Organization,
            "internal_organization": FacilityOrganization,
            "facility": Facility,
        }
        for field, model in targets.items():
            if identifier := getattr(self, field):
                setattr(obj, field, get_object_or_404(model, external_id=identifier))
        validate_internal_organization_facility(obj)
        if obj.internal_organization_id is not None:
            obj.facility_id = obj.internal_organization.facility_id
        obj.care_team = deserialize_care_team(self.care_team)
        assign_questionnaire_mappings(obj, self.questionnaires)


class ReferralAvailabilityUpdateSpec(EMRResource):
    __model__ = ReferralAvailability
    __exclude__ = ["care_team", "questionnaires"]
    name: str | MISSING = Field(default=MISSING, min_length=1, max_length=255)
    description: str | MISSING = MISSING
    status: ReferralAvailabilityStatus | MISSING = MISSING
    is_public: bool | MISSING = MISSING
    care_team: list[EncounterCareTeamMemberSpec] | MISSING = MISSING
    questionnaires: ReferralQuestionnaireMappings | MISSING = MISSING

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be empty")
        return value.strip()

    def perform_extra_deserialization(self, is_update, obj):
        if self.care_team is not MISSING:
            obj.care_team = deserialize_care_team(self.care_team)
        if self.questionnaires is not MISSING:
            assign_questionnaire_mappings(obj, self.questionnaires)


class ReferralAvailabilityReadSpec(ReferralAvailabilitySpec):
    entity_type: ReferralEntityType
    external_organization: UUID4 | None = None
    internal_organization: UUID4 | None = None
    facility: UUID4 | None = None
    external_entity: dict
    care_team: list[dict]
    created_date: datetime
    modified_date: datetime
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        for field in ("external_organization", "internal_organization", "facility"):
            entity = getattr(obj, field)
            mapping[field] = entity.external_id if entity else None
        mapping["care_team"] = serialize_care_team(obj.care_team)
        cls.serialize_audit_users(mapping, obj)


class ReferralAvailabilityRetrieveSpec(ReferralAvailabilityReadSpec):
    questionnaires: list[dict]

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["questionnaires"] = [
            {
                "id": str(link.questionnaire.external_id),
                "slug": link.questionnaire.slug,
                "title": link.questionnaire.title,
                "status": link.questionnaire.status,
                "questionnaire_type": link.questionnaire_type,
            }
            for link in ReferralAvailabilityQuestionnaire.objects.filter(
                availability=obj, questionnaire__deleted=False
            ).select_related("questionnaire")
        ]
