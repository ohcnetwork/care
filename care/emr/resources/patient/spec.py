import datetime
import uuid
from enum import Enum

from django.utils import timezone
from pydantic import UUID4, Field, field_validator, model_validator

from care.emr.models import Organization
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource, PhoneNumber


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
    death_datetime: datetime.datetime | None = None
    blood_group: BloodGroupChoices | None = None


class PatientCreateSpec(PatientBaseSpec):
    geo_organization: UUID4
    date_of_birth: datetime.date | None = None

    age: int | None = None

    @model_validator(mode="after")
    def validate_age(self):
        if not (self.age or self.date_of_birth):
            raise ValueError("Either age or date of birth is required")
        return self

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
        if not is_update:
            if self.age:
                obj.year_of_birth = timezone.now().date().year - self.age
            else:
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


class PatientRetrieveSpec(PatientListSpec):
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
