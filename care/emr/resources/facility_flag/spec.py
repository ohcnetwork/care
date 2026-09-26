from pydantic import UUID4, field_validator

from care.emr.resources.base import EMRResource
from care.emr.resources.facility.spec import FacilityBareMinimumSpec
from care.facility.models import FacilityFlag
from care.facility.models.facility import Facility
from care.utils.registries.feature_flag import FlagRegistry, FlagType
from care.utils.shortcuts import get_object_or_404


class FacilityFlagBaseSpec(EMRResource):
    __model__ = FacilityFlag
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    flag: str


class FacilityFlagCreateSpec(FacilityFlagBaseSpec):
    facility: UUID4

    @field_validator("flag")
    @classmethod
    def validate_flag_name(cls, flag_name):
        FlagRegistry.validate_flag_name(FlagType.FACILITY, flag_name)
        return flag_name

    def perform_extra_deserialization(self, is_update, obj):
        if not is_update:
            obj.facility = get_object_or_404(Facility, external_id=self.facility)


class FacilityFlagUpdateSpec(FacilityFlagBaseSpec):
    @field_validator("flag")
    @classmethod
    def validate_flag_name(cls, flag_name):
        FlagRegistry.validate_flag_name(FlagType.FACILITY, flag_name)
        return flag_name


class FacilityFlagReadSpec(FacilityFlagBaseSpec):
    facility: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["facility"] = FacilityBareMinimumSpec.serialize(obj.facility).to_json()


class FacilityFlagRetrieveSpec(FacilityFlagReadSpec):
    pass
