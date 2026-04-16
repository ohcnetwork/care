import datetime

from django.utils import timezone
from pydantic import UUID4, field_validator, model_validator

from care.emr.extensions.base import ExtensionResource
from care.emr.extensions.validator import ExtensionValidator
from care.emr.models import Organization
from care.emr.models.patient import Patient
from care.emr.resources.base import EMRResource
from care.emr.resources.patient.spec import BloodGroupChoices, GenderChoices


class PatientOTPBaseSpec(EMRResource):
    __model__ = Patient
    __exclude__ = ["geo_organization"]
    ___extension_resource_type__ = ExtensionResource.patient
    id: UUID4 = None


class PatientOTPReadSpec(PatientOTPBaseSpec):
    name: str
    gender: str
    phone_number: str
    emergency_phone_number: str
    address: str
    pincode: int
    date_of_birth: datetime.date
    year_of_birth: int
    geo_organization: dict | None = None
    blood_group: BloodGroupChoices | None = None
    extensions: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.geo_organization:
            mapping["geo_organization"] = obj.geo_organization.get_parent_json()


class PatientOTPWriteSpec(ExtensionValidator, PatientOTPBaseSpec):
    name: str
    gender: GenderChoices
    date_of_birth: datetime.date | None = None
    age: int | None = None
    address: str
    pincode: int
    geo_organization: UUID4
    blood_group: BloodGroupChoices | None = None

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
        if not is_update:
            obj.geo_organization = Organization.objects.get(
                external_id=self.geo_organization
            )
            if self.age:
                obj.year_of_birth = timezone.now().date().year - self.age
            else:
                obj.year_of_birth = self.date_of_birth.year
