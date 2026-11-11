"""
Spec for Tag Configs
Tag configs include what tags are available for a resource and their configuration
"""

from enum import Enum

from django.db.models.signals import post_save
from pydantic import UUID4, BaseModel, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from rest_framework.exceptions import ValidationError

from care.emr.models.organization import FacilityOrganization, Organization
from care.emr.models.tag_config import TagConfig
from care.emr.resources.base import EMRResource, cacheable, model_string
from care.emr.resources.tag.cache_invalidation import invalidate_tag_config_cache
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class TagCategoryChoices(str, Enum):
    diet = "diet"
    drug = "drug"
    lab = "lab"
    admin = "admin"
    contact = "contact"
    clinical = "clinical"
    behavioral = "behavioral"
    research = "research"
    advance_directive = "advance_directive"
    safety = "safety"


class TagResource(str, Enum):
    encounter = "encounter"
    activity_definition = "activity_definition"
    service_request = "service_request"
    charge_item = "charge_item"
    charge_item_definition = "charge_item_definition"
    patient = "patient"
    token_booking = "token_booking"
    medication_request_prescription = "medication_request_prescription"
    supply_request_order = "supply_request_order"
    supply_delivery_order = "supply_delivery_order"
    account = "account"
    location = "location"


def tag_resource_to_model(resource_type: TagResource):
    from care.emr.models.account import Account
    from care.emr.models.activity_definition import ActivityDefinition
    from care.emr.models.charge_item import ChargeItem
    from care.emr.models.charge_item_definition import ChargeItemDefinition
    from care.emr.models.encounter import Encounter
    from care.emr.models.location import FacilityLocation
    from care.emr.models.medication_request import MedicationRequestPrescription
    from care.emr.models.patient import Patient
    from care.emr.models.scheduling.booking import TokenBooking
    from care.emr.models.service_request import ServiceRequest
    from care.emr.models.supply_delivery import DeliveryOrder
    from care.emr.models.supply_request import RequestOrder

    if resource_type == TagResource.encounter:
        return Encounter
    if resource_type == TagResource.activity_definition:
        return ActivityDefinition
    if resource_type == TagResource.service_request:
        return ServiceRequest
    if resource_type == TagResource.charge_item:
        return ChargeItem
    if resource_type == TagResource.charge_item_definition:
        return ChargeItemDefinition
    if resource_type == TagResource.patient:
        return Patient
    if resource_type == TagResource.token_booking:
        return TokenBooking
    if resource_type == TagResource.medication_request_prescription:
        return MedicationRequestPrescription
    if resource_type == TagResource.supply_request_order:
        return RequestOrder
    if resource_type == TagResource.supply_delivery_order:
        return DeliveryOrder
    if resource_type == TagResource.account:
        return Account
    if resource_type == TagResource.location:
        return FacilityLocation
    return None


class TagStatus(str, Enum):
    active = "active"
    archived = "archived"


class TagConfigMetadata(BaseModel):
    color: str | None = None
    icon: str | None = None


class ExpiryOffset(BaseModel):
    days: int | MISSING = MISSING
    hours: int | MISSING = MISSING
    minutes: int | MISSING = MISSING
    seconds: int | MISSING = MISSING


class TagSetRequest(BaseModel):
    tag: UUID4
    expiry_offset: ExpiryOffset | None = None


class TagConfigExpiryMetadata(BaseModel):
    modification_allowed: bool | MISSING = MISSING
    expiry_offset: ExpiryOffset | MISSING = MISSING
    autoset_expiry: bool | MISSING = MISSING

    @model_validator(mode="after")
    def validate_autoset_expiry(self):
        if self.autoset_expiry is True and self.expiry_offset is MISSING:
            raise ValueError("Expiry offset is required when autoset expiry is set")
        return self


class TagConfigBaseSpec(EMRResource):
    __model__ = TagConfig
    __exclude__ = ["facility", "facility_organization", "organization", "parent"]
    id: UUID4 | None = None
    display: str
    category: TagCategoryChoices
    description: str | None
    priority: int = 100
    status: TagStatus
    metadata: TagConfigMetadata | None = None
    expiry_metadata: TagConfigExpiryMetadata | MISSING = MISSING


class TagConfigUpdateSpec(TagConfigBaseSpec):
    facility_organization: UUID4 | None = None
    organization: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.organization:
            obj.organization = get_object_or_404(
                Organization.objects.only("id"), external_id=self.organization
            )
        else:
            obj.organization = None
        if self.facility_organization:
            obj.facility_organization = get_object_or_404(
                FacilityOrganization.objects.only("id"),
                external_id=self.facility_organization,
                facility=obj.facility,
            )
        else:
            obj.facility_organization = None


class TagConfigWriteSpec(TagConfigBaseSpec):
    facility: UUID4 | None = None
    facility_organization: UUID4 | None = None
    organization: UUID4 | None = None
    parent: UUID4 | None = None
    resource: TagResource

    @model_validator(mode="after")
    def validate_exists(self):
        """
        Validate that the facility, facility organization,
        organization, and parent are in order
        """
        facility = None
        if self.facility:
            facility = get_object_or_404(Facility, external_id=self.facility)
            if (
                self.facility_organization
                and not FacilityOrganization.objects.filter(
                    external_id=self.facility_organization,
                    facility=facility,
                ).exists()
            ):
                err = "Facility Organization not found"
                raise ValidationError(err)
        if (
            self.organization
            and not Organization.objects.filter(external_id=self.organization).exists()
        ):
            err = "Organization not found"
            raise ValidationError(err)
        if self.parent:
            config = TagConfig.objects.filter(
                external_id=self.parent, resource=self.resource
            )
            if facility:
                config = config.filter(facility=facility)
            if not config.exists():
                err = "Parent tag config not found"
                raise ValueError(err)
        return self

    @model_validator(mode="after")
    def validate_organizations(self):
        """
        Validate edge conditions
        """
        if not self.facility and self.facility_organization:
            err = "Facility Organization not allowed in instance level tag configs"
            raise ValueError(err)
        return self

    def perform_extra_deserialization(self, is_update, obj):
        if self.parent:
            obj.parent = TagConfig.objects.only("id").get(external_id=self.parent)
        else:
            obj.parent = None
        if self.organization:
            obj.organization = Organization.objects.only("id").get(
                external_id=self.organization
            )
        if self.facility:
            obj.facility = Facility.objects.only("id").get(external_id=self.facility)
            if self.facility_organization:
                obj.facility_organization = FacilityOrganization.objects.only("id").get(
                    external_id=self.facility_organization, facility=obj.facility
                )


@cacheable
class TagConfigReadSpec(TagConfigBaseSpec):
    level_cache: int = 0
    system_generated: bool
    has_children: bool
    parent: dict | None
    resource: str
    facility: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.facility.spec import FacilityBareMinimumSpec

        mapping["id"] = obj.external_id
        parent = obj.get_parent_json()
        if parent:
            mapping["parent"] = parent
        if obj.facility:
            mapping["facility"] = FacilityBareMinimumSpec.serialize(
                obj.facility
            ).to_json()


class TagConfigRetrieveSpec(TagConfigReadSpec):
    created_by: dict
    updated_by: dict
    facility_organization: dict | None = None
    organization: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.facility_organization.spec import (
            FacilityOrganizationReadSpec,
        )
        from care.emr.resources.organization.spec import OrganizationReadSpec

        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)
        if obj.facility_organization:
            mapping["facility_organization"] = FacilityOrganizationReadSpec.serialize(
                obj.facility_organization
            ).to_json()
        if obj.organization:
            mapping["organization"] = OrganizationReadSpec.serialize(
                obj.organization
            ).to_json()


post_save.connect(
    invalidate_tag_config_cache,
    sender=TagConfig,
    dispatch_uid=f"invalidate_tag_config_cache:{model_string(TagConfig)}",
)
