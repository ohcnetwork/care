import datetime
from enum import Enum

from pydantic import UUID4, model_validator

from care.emr.models import Encounter, FacilityLocationEncounter
from care.emr.models.location import FacilityLocation
from care.emr.resources.base import EMRResource
from care.emr.resources.common import Coding
from care.emr.resources.user.spec import UserSpec


class LocationEncounterAvailabilityStatusChoices(str, Enum):
    planned = "planned"
    active = "active"
    reserved = "reserved"
    completed = "completed"


class LocationAvailabilityStatusChoices(str, Enum):
    available = "available"
    unavailable = "unavailable"


class StatusChoices(str, Enum):
    active = "active"
    inactive = "inactive"
    unknown = "unknown"


class FacilityLocationOperationalStatusChoices(str, Enum):
    C = "C"
    H = "H"
    O = "O"  # noqa E741
    U = "U"
    K = "K"
    I = "I"  # noqa E741


class FacilityLocationModeChoices(str, Enum):
    instance = "instance"
    kind = "kind"


class FacilityLocationFormChoices(str, Enum):
    si = "si"
    bu = "bu"
    wi = "wi"
    wa = "wa"
    lvl = "lvl"
    co = "co"
    ro = "ro"
    bd = "bd"
    ve = "ve"
    ho = "ho"
    ca = "ca"
    rd = "rd"
    area = "area"
    jdn = "jdn"
    vi = "vi"


class FacilityLocationBaseSpec(EMRResource):
    __model__ = FacilityLocation
    __exclude__ = ["parent", "facility", "organizations", "root_location"]

    id: UUID4 | None = None


class FacilityLocationSpec(FacilityLocationBaseSpec):
    status: StatusChoices
    operational_status: FacilityLocationOperationalStatusChoices
    name: str
    description: str
    location_type: Coding | None = None
    form: FacilityLocationFormChoices


class FacilityLocationUpdateSpec(FacilityLocationSpec):
    pass


class FacilityLocationWriteSpec(FacilityLocationSpec):
    parent: UUID4 | None = None
    organizations: list[UUID4]
    mode: FacilityLocationModeChoices

    @model_validator(mode="after")
    def validate_parent_organization(self):
        if (
            self.parent
            and not FacilityLocation.objects.filter(
                external_id=self.parent, mode=FacilityLocationModeChoices.kind.value
            ).exists()
        ):
            err = "Parent not found"
            raise ValueError(err)
        return self

    def perform_extra_deserialization(self, is_update, obj):
        if self.parent:
            obj.parent = FacilityLocation.objects.get(external_id=self.parent)
        else:
            obj.parent = None
        obj.availability_status = LocationAvailabilityStatusChoices.available.value


class FacilityLocationListSpec(FacilityLocationSpec):
    parent: dict
    mode: str
    has_children: bool
    availability_status: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["parent"] = obj.get_parent_json()


class FacilityLocationRetrieveSpec(FacilityLocationListSpec):
    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by)


class FacilityLocationEncounterBaseSpec(EMRResource):
    __model__ = FacilityLocationEncounter
    __exclude__ = ["encounter", "location"]

    id: UUID4 | None = None


class FacilityLocationEncounterCreateSpec(FacilityLocationEncounterBaseSpec):
    status: LocationEncounterAvailabilityStatusChoices
    encounter: UUID4
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime | None = None

    @model_validator(mode="after")
    def validate_encounter(self):
        if not Encounter.objects.filter(external_id=self.encounter).exists():
            err = "Encounter not found"
            raise ValueError(err)
        return self

    def perform_extra_deserialization(self, is_update, obj):
        obj.encounter = Encounter.objects.get(external_id=self.encounter)


class FacilityLocationEncounterUpdateSpec(FacilityLocationEncounterBaseSpec):
    status: LocationEncounterAvailabilityStatusChoices

    start_datetime: datetime.datetime
    end_datetime: datetime.datetime | None = None


class FacilityLocationEncounterListSpec(FacilityLocationEncounterBaseSpec):
    encounter: UUID4
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime | None = None
    status: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class FacilityLocationEncounterListSpecWithLocation(FacilityLocationEncounterListSpec):
    location: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["location"] = FacilityLocationListSpec.serialize(obj.location).to_json()


class FacilityLocationEncounterReadSpec(FacilityLocationEncounterBaseSpec):
    encounter: UUID4
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime | None = None
    status: str

    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)
