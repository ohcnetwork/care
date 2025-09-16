from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4

from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.location import FacilityLocation
from care.emr.models.organization import FacilityOrganization
from care.emr.resources.base import EMRResource
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
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
    managing_organization: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.managing_organization:
            obj.managing_organization = get_object_or_404(
                FacilityOrganization.objects.all().only("id"),
                external_id=self.managing_organization,
            )
        return super().perform_extra_deserialization(is_update, obj)


class HealthcareServiceReadSpec(BaseHealthcareServiceSpec):
    """Healthcare service read specification"""

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class HealthcareServiceRetrieveSpec(HealthcareServiceReadSpec):
    """Healthcare service retrieve specification"""

    locations: list[dict]
    managing_organization: dict | None = None

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
        if obj.managing_organization:
            mapping["managing_organization"] = FacilityOrganizationReadSpec.serialize(
                obj.managing_organization
            ).to_json()
