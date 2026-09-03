from enum import Enum

from django.db.models import Q
from pydantic import UUID4, field_validator, model_validator
from rest_framework.exceptions import ValidationError

from care.emr.models.organization import FacilityOrganization
from care.emr.models.valueset import ValueSet as ValuesetDatabaseModel
from care.emr.resources.base import EMRResource
from care.emr.resources.common.valueset import ValueSetCompose
from care.emr.utils.slug_type import SlugType
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class ValueSetAuthContext(str, Enum):
    instance = "instance"
    facility_organization = "facility_organization"
    facility = "facility"
    user = "user"


class ValueSetStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    retired = "retired"
    unknown = "unknown"


class ValueSetBaseSpec(EMRResource):
    __model__ = ValuesetDatabaseModel

    id: UUID4 = None
    slug: SlugType
    name: str
    description: str
    compose: ValueSetCompose
    status: ValueSetStatusOptions


class ValueSetSpec(ValueSetBaseSpec):
    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str, info):
        if not name.strip():
            raise ValueError("Name cannot be empty")
        return name.strip()

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, slug: str, info) -> str:
        queryset = ValuesetDatabaseModel.objects.filter(slug=slug)
        context = cls.get_serializer_context(info)
        if context.get("is_update", False):
            queryset = queryset.exclude(id=info.context["object"].id)
        if queryset.exists():
            err = "Slug must be unique"
            raise ValueError(err)
        return slug

    def perform_extra_deserialization(self, is_update, obj):
        obj.compose = self.compose.model_dump(exclude_defaults=True, exclude_none=True)


class ValueSetCreateSpec(ValueSetBaseSpec):
    auth_context: ValueSetAuthContext
    facility: UUID4 | None = None
    facility_organization: UUID4 | None = None
    inherited: bool
    parent: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if obj.auth_context in (ValueSetAuthContext.facility, ValueSetAuthContext.user):
            obj.facility = get_object_or_404(
                Facility.objects.only("id"), external_id=self.facility
            )

        if obj.auth_context == ValueSetAuthContext.facility_organization:
            obj.facility_organization = get_object_or_404(
                FacilityOrganization, external_id=self.facility_organization
            )
            obj.facility = obj.facility_organization.facility
            obj.internal_organization_cache = [
                *obj.facility_organization.parent_cache,
                obj.facility_organization.id,
            ]

        if self.parent:
            allowed_parent_scope = Q(auth_context=ValueSetAuthContext.instance)
            if obj.facility_id:
                allowed_parent_scope |= Q(
                    auth_context__in=(
                        ValueSetAuthContext.facility,
                        ValueSetAuthContext.facility_organization,
                    ),
                    facility=obj.facility,
                )
            obj.parent = ValuesetDatabaseModel.objects.filter(
                allowed_parent_scope,
                external_id=self.parent,
            ).first()
            if not obj.parent:
                err = "Parent not found"
                raise ValidationError(err)
            if self.inherited:
                obj.slug = obj.parent.slug

    @field_validator("parent")
    @classmethod
    def validate_parent(cls, parent: UUID4):
        if (
            parent
            and not ValuesetDatabaseModel.objects.filter(external_id=parent).exists()
        ):
            err = "Parent not found"
            raise ValueError(err)
        return parent

    @field_validator("facility")
    @classmethod
    def validate_facility(cls, facility: UUID4):
        if facility and not Facility.objects.filter(external_id=facility).exists():
            err = "Facility not found"
            raise ValueError(err)
        return facility

    @field_validator("facility_organization")
    @classmethod
    def validate_facility_organization(cls, facility_organization: UUID4):
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
    def validate_unique_id(self):
        if self.auth_context == ValueSetAuthContext.user and not self.facility:
            raise ValueError("Facility is required")
        if self.auth_context == ValueSetAuthContext.facility and not self.facility:
            raise ValueError("Facility is required")
        if (
            self.auth_context == ValueSetAuthContext.facility_organization
            and not self.facility_organization
        ):
            raise ValueError("Facility organization is required")
        return self

    @model_validator(mode="after")
    def validate_inheritance(self):
        if self.inherited and not self.parent:
            raise ValueError("Parent is required for inherited value sets")
        return self

    @model_validator(mode="after")
    def validate_slug_system(self):
        if self.inherited:
            return self
        if "system-" in self.slug:
            err = "Cannot create valueset with system like slug"
            raise ValueError(err)
        return self

    # @model_validator(mode="after")
    # def validate_slug(self, info):
    #     # Uniqueness changes based on the auth context
    #     if self.auth_context == ValueSetAuthContext.instance:
    #         queryset = ValuesetDatabaseModel.objects.filter(slug=self.slug)
    #     elif self.auth_context == ValueSetAuthContext.facility:
    #         queryset = ValuesetDatabaseModel.objects.filter(
    #             facility__external_id=self.facility
    #         )
    #     elif self.auth_context == ValueSetAuthContext.facility_organization:
    #         queryset = ValuesetDatabaseModel.objects.filter(
    #             facility_organization__organization__external_id=self.facility_organization
    #         )
    #     elif self.auth_context == ValueSetAuthContext.user:
    #         queryset = ValuesetDatabaseModel.objects.filter(
    #             created_by=self.get_serializer_context(info)["user"]
    #         )
    #     else:
    #         raise ValueError("Invalid auth context")
    #     if queryset.exists():
    #         err = "Slug must be unique"
    #         raise ValueError(err)

    #     return self


class ValueSetUpdateSpec(ValueSetBaseSpec):
    @model_validator(mode="after")
    def validate_slug_system(self, info):
        current_obj = info.context["object"]
        if current_obj.is_system_defined or current_obj.inherited:
            return self
        if "system-" in self.slug:
            err = "Cannot create valueset with system like slug"
            raise ValueError(err)
        return self


class ValueSetMinimalReadSpec(ValueSetBaseSpec):
    is_system_defined: bool = False

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class ValueSetReadSpec(ValueSetMinimalReadSpec):
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)


ValueSetSpec.model_rebuild()
