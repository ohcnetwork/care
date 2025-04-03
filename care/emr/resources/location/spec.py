import datetime
from enum import Enum

from pydantic import UUID4, Field, model_validator

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
    __exclude__ = [
        "parent",
        "facility",
        "organizations",
        "root_location",
        "current_encounter",
    ]

    id: UUID4 | None = None


MIN_SORT_INDEX = 0
MAX_SORT_INDEX = 10000


class FacilityLocationSpec(FacilityLocationBaseSpec):
    status: StatusChoices
    operational_status: FacilityLocationOperationalStatusChoices
    name: str
    description: str
    location_type: Coding | None = None
    form: FacilityLocationFormChoices
    sort_index: int | None = Field(
        default=0,
        ge=MIN_SORT_INDEX,
        le=MAX_SORT_INDEX,
    )


class FacilityLocationUpdateSpec(FacilityLocationSpec):
    pass


class FacilityLocationWriteSpec(FacilityLocationSpec):
    parent: UUID4 | None = None
    organizations: list[UUID4]
    mode: FacilityLocationModeChoices

    @model_validator(mode="after")
    def validate_parent_organization(self):
        if self.parent:
            try:
                parent_location = FacilityLocation.objects.get(external_id=self.parent)
            except FacilityLocation.DoesNotExist as e:
                raise ValueError("Parent not found") from e
            if parent_location.mode == FacilityLocationModeChoices.instance.value:
                raise ValueError("Instances cannot have children")
        return self

    def perform_extra_deserialization(self, is_update, obj):
        if self.parent:
            obj.parent = FacilityLocation.objects.get(external_id=self.parent)
        else:
            obj.parent = None


class FacilityLocationListSpec(FacilityLocationSpec):
    parent: dict
    mode: str
    has_children: bool
    availability_status: str
    current_encounter: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.encounter.spec import EncounterListSpec

        mapping["id"] = obj.external_id
        mapping["parent"] = obj.get_parent_json()
        if obj.current_encounter:
            mapping["current_encounter"] = EncounterListSpec.serialize(
                obj.current_encounter
            ).to_json()


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
    end_datetime: datetime.datetime | None


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
