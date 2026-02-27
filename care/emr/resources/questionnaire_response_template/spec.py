from datetime import datetime

from pydantic import UUID4, BaseModel, field_validator, model_validator

from care.emr.models.activity_definition import ActivityDefinition
from care.emr.models.organization import FacilityOrganization
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponseTemplate
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.medication.request.spec import MedicationRequestAbstractSpec
from care.emr.resources.service_request.spec import ServiceRequestUpdateSpec
from care.emr.resources.user.spec import UserSpec
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class QuestionnaireAnswer(BaseModel):
    question_id: str
    answer: dict
    meta: dict


class MedicationRequestTemplateSpec(MedicationRequestAbstractSpec):
    requested_product: str | None = None

    @field_validator("requested_product")
    @classmethod
    def validate_requested_product(cls, requested_product):
        if requested_product is None:
            return requested_product
        if not ProductKnowledge.objects.filter(slug=requested_product).exists():
            raise ValueError("Product knowledge not found")
        return requested_product


class ActivityDefinitionTemplateSpec(BaseModel):
    slug: str
    service_request: ServiceRequestUpdateSpec

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, slug):
        if not ActivityDefinition.objects.filter(slug=slug).exists():
            raise ValueError("Activity definition not found")
        return slug


class TemplateData(BaseModel):
    medication_request: list[MedicationRequestTemplateSpec] | None = None
    questionnaire: list[QuestionnaireAnswer] | None = None
    activity_definition: list[ActivityDefinitionTemplateSpec] | None = None
    meta: dict | None = None


class QuestionnaireResponseTemplateBaseSpec(EMRResource):
    __model__ = QuestionnaireResponseTemplate
    id: UUID4 | None = None
    template_data: TemplateData
    name: str
    description: str = ""


class QuestionnaireResponseTemplateCreateSpec(QuestionnaireResponseTemplateBaseSpec):
    questionnaire: str | None = None
    facility: UUID4 | None = None
    users: list[str]
    facility_organizations: list[UUID4]

    @model_validator(mode="after")
    def validate_facility(self):
        if not self.facility and self.facility_organizations:
            raise ValueError(
                "Facility is required if facility organizations are provided"
            )
        return self

    def perform_extra_deserialization(self, is_update, obj):
        if self.questionnaire:
            obj.questionnaire = get_object_or_404(
                Questionnaire, slug=self.questionnaire
            )
        if self.facility:
            obj.facility = get_object_or_404(Facility, external_id=self.facility)
        obj.available_keys = []
        for key in list(obj.template_data.keys()):
            if obj.template_data[key]:
                obj.available_keys.append(key)
        return super().perform_extra_deserialization(is_update, obj)


class QuestionnaireResponseTemplateUpdateSpec(QuestionnaireResponseTemplateBaseSpec):
    users: list[str]
    facility_organizations: list[UUID4]

    def perform_extra_deserialization(self, is_update, obj):
        obj.available_keys = []
        for key in list(obj.template_data.keys()):
            if obj.template_data[key]:
                obj.available_keys.append(key)


class QuestionnaireResponseTemplateReadSpec(QuestionnaireResponseTemplateBaseSpec):
    created_date: datetime
    modified_date: datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = str(obj.external_id)


class QuestionnaireResponseTemplateRetrieveSpec(QuestionnaireResponseTemplateReadSpec):
    users: list[dict] = []

    facility_organizations: list[dict] = []
    created_by: dict = {}
    updated_by: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)
        mapping["users"] = []
        for user in obj.users:
            mapping["users"].append(model_from_cache(UserSpec, id=user))
        mapping["facility_organizations"] = []
        for facility_organization in obj.facility_organizations:
            facility_organization_obj = FacilityOrganization.objects.filter(
                id=facility_organization
            ).first()
            if facility_organization_obj:
                mapping["facility_organizations"].append(
                    FacilityOrganizationReadSpec.serialize(
                        facility_organization_obj
                    ).to_json()
                )
