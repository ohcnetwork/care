from enum import Enum

from pydantic import UUID4

from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.location import FacilityLocation
from care.emr.resources.base import EMRResource
from care.emr.resources.healthcare_service.valueset import (
    HEALTHCARE_SERVICE_TYPE_CODE_VALUESET,
)
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class HealthcareServiceInternalType(str, Enum):
    pharmacy = "pharmacy"
    lab = "lab"


class BaseHealthcareServiceSpec(EMRResource):
    """Base model for healthcare service"""

    __model__ = HealthcareService
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    service_type: (
        ValueSetBoundCoding[HEALTHCARE_SERVICE_TYPE_CODE_VALUESET.slug] | None
    ) = None
    internal_type: HealthcareServiceInternalType | None = None
    name: str
    styling_metadata: dict = {}
    extra_details: str = ""


class HealthcareServiceWriteSpec(BaseHealthcareServiceSpec):
    """Healthcare service write specification"""

    locations: list[UUID4] = []


class HealthcareServiceReadSpec(BaseHealthcareServiceSpec):
    """Healthcare service read specification"""

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class HealthcareServiceRetrieveSpec(HealthcareServiceReadSpec):
    """Healthcare service retrieve specification"""

    locations: list[dict]

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        locations = []
        for location in obj.locations:
            try:
                locations.append(
                    FacilityLocationListSpec.serialize(
                        FacilityLocation.objects.get(id=location)
                    ).to_json()
                )
            except Exception:  # noqa S110
                pass
        mapping["locations"] = locations
