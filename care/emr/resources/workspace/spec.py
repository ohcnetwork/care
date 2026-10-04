from enum import Enum

from pydantic import UUID4, field_validator, model_validator

from care.emr.models.organization import FacilityOrganization
from care.emr.models.workspace import Workspace
from care.emr.resources.base import EMRResource
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class WorkspaceStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class WorkspaceAuthContext(str, Enum):
    instance = "instance"
    facility_organization = "facility_organization"
    facility = "facility"
    user = "user"


class WorkspaceBaseSpec(EMRResource):
    __model__ = Workspace

    id: UUID4 = None
    name: str
    description: str
    template: dict
    status: WorkspaceStatus


class WorkspaceCreateSpec(WorkspaceBaseSpec):
    auth_context: WorkspaceAuthContext
    facility: UUID4 | None = None
    facility_organization: UUID4 | None = None
    inherited: bool

    def perform_extra_deserialization(self, is_update, obj):
        if obj.auth_context in (
            WorkspaceAuthContext.facility,
            WorkspaceAuthContext.user,
        ):
            obj.facility = get_object_or_404(
                Facility.objects.only("id"), external_id=self.facility
            )

        if obj.auth_context == WorkspaceAuthContext.facility_organization:
            obj.facility_organization = get_object_or_404(
                FacilityOrganization, external_id=self.facility_organization
            )
            obj.facility = obj.facility_organization.facility
            obj.internal_organization_cache = [
                *obj.facility_organization.parent_cache,
                obj.facility_organization.id,
            ]

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
        if self.auth_context == WorkspaceAuthContext.user and not self.facility:
            raise ValueError("Facility is required")
        if self.auth_context == WorkspaceAuthContext.facility and not self.facility:
            raise ValueError("Facility is required")
        if (
            self.auth_context == WorkspaceAuthContext.facility_organization
            and not self.facility_organization
        ):
            raise ValueError("Facility organization is required")
        return self


class WorkspaceUpdateSpec(WorkspaceBaseSpec):
    pass


class WorkspaceMinimalReadSpec(WorkspaceBaseSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class WorkspaceReadSpec(WorkspaceMinimalReadSpec):
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)
