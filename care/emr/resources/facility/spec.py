from pydantic import UUID4

from care.emr.models import Organization
from care.emr.resources.base import EMRResource
from care.emr.resources.organization.spec import OrganizationReadSpec
from care.emr.resources.user.spec import UserSpec
from care.facility.models import (
    REVERSE_FACILITY_TYPES,
    REVERSE_REVERSE_FACILITY_TYPES,
    Facility,
)


class FacilityBareMinimumSpec(EMRResource):
    __model__ = Facility
    __exclude__ = ["geo_organization"]
    id: UUID4 | None = None
    name: str


class FacilityBaseSpec(FacilityBareMinimumSpec):
    description: str
    longitude: float | None = None
    latitude: float | None = None
    pincode: int
    address: str
    phone_number: str
    middleware_address: str | None = None
    facility_type: str
    is_public: bool = False


class FacilityCreateSpec(FacilityBaseSpec):
    geo_organization: UUID4
    features: list[int]

    def perform_extra_deserialization(self, is_update, obj):
        obj.geo_organization = Organization.objects.filter(
            external_id=self.geo_organization, org_type="govt"
        ).first()
        obj.facility_type = REVERSE_REVERSE_FACILITY_TYPES[self.facility_type]


class FacilityReadSpec(FacilityBaseSpec):
    features: list[int]
    cover_image_url: str
    read_cover_image_url: str
    geo_organization: dict = {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["read_cover_image_url"] = obj.read_cover_image_url()
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by)
        mapping["facility_type"] = REVERSE_FACILITY_TYPES[obj.facility_type]
        if obj.geo_organization:
            mapping["geo_organization"] = OrganizationReadSpec.serialize(
                obj.geo_organization
            ).to_json()


class FacilityRetrieveSpec(FacilityReadSpec):
    flags: list[str] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["flags"] = obj.get_facility_flags()
