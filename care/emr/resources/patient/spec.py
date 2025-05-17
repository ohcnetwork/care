import datetime
import uuid
from enum import Enum

from django.utils import timezone
from pydantic import UUID4, Field, field_validator

from care.emr.models import Organization
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource, PhoneNumber
from care.emr.resources.permissions import PatientPermissionsMixin
from care.emr.utils.datetime_type import StrictTZAwareDateTime
from care.utils.time_util import care_now


class BloodGroupChoices(str, Enum):
    A_negative = "A_negative"
    A_positive = "A_positive"
    B_negative = "B_negative"
    B_positive = "B_positive"
    AB_negative = "AB_negative"
    AB_positive = "AB_positive"
    O_negative = "O_negative"
    O_positive = "O_positive"
    unknown = "unknown"


class GenderChoices(str, Enum):
    male = "male"
    female = "female"
    non_binary = "non_binary"
    transgender = "transgender"


class PatientBaseSpec(EMRResource):
    __model__ = Patient
    __exclude__ = ["geo_organization"]
    __store_metadata__ = True

    id: UUID4 | None = None
    name: str = Field(max_length=200)
    gender: GenderChoices
    phone_number: PhoneNumber = Field(max_length=14)
    emergency_phone_number: PhoneNumber | None = Field(None, max_length=14)
    address: str
    permanent_address: str
    pincode: int
    deceased_datetime: StrictTZAwareDateTime | None = None
    blood_group: BloodGroupChoices | None = None

    @field_validator("deceased_datetime")
    @classmethod
    def validate_deceased_datetime(cls, deceased_datetime):
        if deceased_datetime is None:
            return None
        if deceased_datetime > care_now():
            raise ValueError("Deceased datetime cannot be in the future")
        return deceased_datetime


class PatientCreateSpec(PatientBaseSpec):
    geo_organization: UUID4
    date_of_birth: datetime.date | None = None

    age: int | None = None

    @field_validator("geo_organization")
    @classmethod
    def validate_geo_organization(cls, geo_organization):
        if not Organization.objects.filter(
            org_type="govt", external_id=geo_organization
        ).exists():
            raise ValueError("Geo Organization does not exist")
        return geo_organization

    def perform_extra_deserialization(self, is_update, obj):
        obj.geo_organization = Organization.objects.get(
            external_id=self.geo_organization
        )
        if self.age:
            # override dob if user chooses to update age
            obj.date_of_birth = None
            obj.year_of_birth = timezone.now().date().year - self.age
        else:
            obj.year_of_birth = self.date_of_birth.year


class PatientUpdateSpec(PatientBaseSpec):
    name: str | None = Field(default=None, max_length=200)
    gender: GenderChoices | None = None
    phone_number: PhoneNumber | None = Field(default=None, max_length=14)
    emergency_phone_number: PhoneNumber | None = Field(default=None, max_length=14)
    address: str | None = None
    permanent_address: str | None = None
    pincode: int | None = None
    blood_group: BloodGroupChoices | None = None
    date_of_birth: datetime.date | None = None
    age: int | None = None
    geo_organization: UUID4 | None = None

    @field_validator("geo_organization")
    @classmethod
    def validate_geo_organization(cls, geo_organization):
        if geo_organization is None:
            return None
        if not Organization.objects.filter(
            org_type="govt", external_id=geo_organization
        ).exists():
            raise ValueError("Geo Organization does not exist")
        return geo_organization

    def perform_extra_deserialization(self, is_update, obj):
        if is_update:
            if self.geo_organization:
                obj.geo_organization = Organization.objects.get(
                    external_id=self.geo_organization
                )
            if self.age is not None:
                obj.date_of_birth = None
                obj.year_of_birth = timezone.now().year - self.age
            elif self.date_of_birth:
                obj.year_of_birth = self.date_of_birth.year


class PatientListSpec(PatientBaseSpec):
    date_of_birth: datetime.date | None = None
    year_of_birth: datetime.date | None = None

    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class PatientPartialSpec(EMRResource):
    __model__ = Patient

    id: UUID4 | None = None
    name: str
    gender: GenderChoices
    phone_number: str
    partial_id: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["partial_id"] = str(obj.external_id)[:5]
        mapping["id"] = str(uuid.uuid4())


class PatientRetrieveSpec(PatientListSpec, PatientPermissionsMixin):
    geo_organization: dict = {}

    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        from care.emr.resources.organization.spec import OrganizationReadSpec
        from care.emr.resources.user.spec import UserSpec

        super().perform_extra_serialization(mapping, obj)
        if obj.geo_organization:
            mapping["geo_organization"] = OrganizationReadSpec.serialize(
                obj.geo_organization
            ).to_json()
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
