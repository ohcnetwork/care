from datetime import datetime
from enum import Enum

from pydantic import UUID4, field_validator

from care.emr.models import Device, DeviceEncounterHistory, DeviceLocationHistory
from care.emr.registries.device_type.device_registry import DeviceTypeRegistry
from care.emr.resources.base import EMRResource
from care.emr.resources.common.contact_point import ContactPoint
from care.emr.resources.encounter.spec import EncounterListSpec
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec


class DeviceStatusChoices(str, Enum):
    active = "active"
    inactive = "inactive"
    entered_in_error = "entered_in_error"


class DeviceAvailabilityStatusChoices(str, Enum):
    lost = "lost"
    damaged = "damaged"
    destroyed = "destroyed"
    available = "available"


class DeviceSpecBase(EMRResource):
    __model__ = Device
    __exclude__ = [
        "facility",
        "managing_organization",
        "current_location",
        "current_encounter",
        "care_metadata",
    ]

    id: UUID4 | None = None

    identifier: str | None = None
    status: DeviceStatusChoices
    availability_status: DeviceAvailabilityStatusChoices
    manufacturer: str | None = None
    manufacture_date: datetime | None = None
    expiration_date: datetime | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    registered_name: str
    user_friendly_name: str | None = None
    model_number: str | None = None
    part_number: str | None = None
    contact: list[ContactPoint] = []


class DeviceCreateSpec(DeviceSpecBase):
    care_type: str | None = None
    care_metadata: dict = {}

    @field_validator("care_type")
    @classmethod
    def validate_care_type(cls, value):
        DeviceTypeRegistry.get_care_device_class(value)
        return value


class DeviceUpdateSpec(DeviceSpecBase):
    care_metadata: dict = {}


class DeviceListSpec(DeviceCreateSpec):
    care_metadata: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.care_type:
            care_device_class = DeviceTypeRegistry.get_care_device_class(obj.care_type)
            mapping["care_metadata"] = care_device_class().list(obj)


class DeviceRetrieveSpec(DeviceListSpec):
    current_encounter: dict | None = None
    current_location: dict

    created_by: dict | None = None
    updated_by: dict | None = None
    managing_organization: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["current_location"] = None
        mapping["current_encounter"] = None
        if obj.current_location:
            mapping["current_location"] = FacilityLocationListSpec.serialize(
                obj.current_location
            ).to_json()
        if obj.current_encounter:
            mapping["current_encounter"] = EncounterListSpec.serialize(
                obj.current_encounter
            ).to_json()
        cls.serialize_audit_users(mapping, obj)
        if obj.care_type:
            care_device_class = DeviceTypeRegistry.get_care_device_class(obj.care_type)
            mapping["care_metadata"] = care_device_class().retrieve(obj)

        if obj.managing_organization:
            mapping["managing_organization"] = FacilityOrganizationReadSpec.serialize(
                obj.managing_organization
            ).to_json()


class DeviceLocationHistoryListSpec(EMRResource):
    __model__ = DeviceLocationHistory
    __exclude__ = [
        "device",
        "location",
    ]
    id: UUID4 = None
    location: dict
    created_by: dict
    start: datetime
    end: datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.location:
            mapping["location"] = FacilityLocationListSpec.serialize(
                obj.location
            ).to_json()
        cls.serialize_audit_users(mapping, obj)


class DeviceEncounterHistoryListSpec(EMRResource):
    __model__ = DeviceEncounterHistory
    __exclude__ = [
        "device",
        "encounter",
    ]
    id: UUID4 = None
    encounter: dict
    created_by: dict
    start: datetime
    end: datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.encounter:
            mapping["encounter"] = EncounterListSpec.serialize(obj.encounter).to_json()
        cls.serialize_audit_users(mapping, obj)
