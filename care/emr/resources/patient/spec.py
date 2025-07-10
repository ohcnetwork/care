import datetime
import re
import uuid
from enum import Enum

from django.utils import timezone
from pydantic import UUID4, BaseModel, Field, field_validator, model_validator

from care.emr.models import Organization
from care.emr.models.patient import (
    Patient,
    PatientIdentifier,
    PatientIdentifierConfigCache,
)
from care.emr.resources.base import EMRResource, PhoneNumber
from care.emr.resources.patient_identifier.spec import PatientIdentifierListSpec
from care.emr.resources.permissions import PatientPermissionsMixin
from care.emr.tagging.base import PatientFacilityTagManager, PatientInstanceTagManager
from care.emr.utils.datetime_type import StrictTZAwareDateTime
from care.facility.models.facility import Facility
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
    __exclude__ = [
        "geo_organization",
        "instance_identifiers",
        "facility_identifiers",
        "instance_tags",
        "facility_tags",
    ]
    __store_metadata__ = True

    id: UUID4 | None = None
    name: str = Field(max_length=200)
    gender: GenderChoices
    phone_number: PhoneNumber = Field(max_length=14)
    emergency_phone_number: PhoneNumber | None = Field(None, max_length=14)
    address: str | None = None
    permanent_address: str | None = None
    pincode: int | None = None
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


def validate_identifier_config(config, value, obj=None):
    queryset = PatientIdentifier.objects.filter(
        config__external_id=config["id"],
        value=value,
    )
    if obj:
        queryset = queryset.exclude(patient=obj)
    if config["config"]["unique"] and queryset.exists():
        err = f"Identifier config {config['config']['system']} is not unique"
        raise ValueError(err)
    if (
        value
        and config["config"]["regex"]
        and not re.match(config["config"]["regex"], value)
    ):
        err = f"Identifier config {config['config']['system']} is not valid"
        raise ValueError(err)


class PatientIdentifierConfigRequest(BaseModel):
    config: UUID4
    value: str


class PatientCreateSpec(PatientBaseSpec):
    geo_organization: UUID4
    date_of_birth: datetime.date | None = None

    age: int | None = None

    identifiers: list[PatientIdentifierConfigRequest] = []

    tags: list[UUID4] = []

    @field_validator("geo_organization")
    @classmethod
    def validate_geo_organization(cls, geo_organization):
        if not Organization.objects.filter(
            org_type="govt", external_id=geo_organization
        ).exists():
            raise ValueError("Geo Organization does not exist")
        return geo_organization

    @model_validator(mode="after")
    def validate_identifiers(self):
        instance_identifier_configs = PatientIdentifierConfigCache.get_instance_config()
        configs = {str(x.config): x for x in self.identifiers}
        for identifier_config in instance_identifier_configs:
            if identifier_config["id"] in configs:
                value = configs[identifier_config["id"]].value
                validate_identifier_config(identifier_config, value)
            elif identifier_config["config"]["required"]:
                err = f"Identifier config {identifier_config['config']['system']} is required"
                raise ValueError(err)
        return self

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
        obj._identifiers = self.identifiers  # noqa: SLF001
        obj._tags = self.tags  # noqa: SLF001


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

    identifiers: list[PatientIdentifierConfigRequest] = []

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
            obj._identifiers = self.identifiers  # noqa: SLF001
            if self.geo_organization:
                obj.geo_organization = Organization.objects.get(
                    external_id=self.geo_organization
                )
            if self.age is not None:
                obj.date_of_birth = None
                obj.year_of_birth = timezone.now().year - self.age
            elif self.date_of_birth:
                obj.year_of_birth = self.date_of_birth.year

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, identifiers, info):
        instance_identifier_configs = PatientIdentifierConfigCache.get_instance_config()
        configs = {str(x.config): x for x in identifiers}
        for identifier_config in instance_identifier_configs:
            if identifier_config["id"] in configs:
                value = configs[identifier_config["id"]].value
                validate_identifier_config(
                    identifier_config, value, info.context.get("object")
                )
            elif identifier_config["config"]["required"]:
                err = f"Identifier config {identifier_config['config']['system']} is required"
                raise ValueError(err)
        return identifiers


class PatientListSpec(PatientBaseSpec):
    date_of_birth: datetime.date | None = None
    year_of_birth: datetime.date | None = None

    created_date: datetime.datetime
    modified_date: datetime.datetime

    instance_tags: list[dict] = []
    facility_tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj, *args, **kwargs):
        mapping["id"] = obj.external_id
        mapping["instance_tags"] = PatientInstanceTagManager().render_tags(obj)
        if kwargs.get("facility"):
            mapping["facility_tags"] = PatientFacilityTagManager(
                kwargs["facility"]
            ).render_tags(obj)


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


class PatientIdentifierResponse(BaseModel):
    config: PatientIdentifierListSpec
    value: str


class PatientRetrieveSpec(PatientListSpec, PatientPermissionsMixin):
    geo_organization: dict = {}

    created_by: dict | None = None
    updated_by: dict | None = None

    instance_identifiers: list[PatientIdentifierResponse] = []
    facility_identifiers: list[PatientIdentifierResponse] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj, *args, **kwargs):
        from care.emr.resources.organization.spec import OrganizationReadSpec
        from care.emr.resources.user.spec import UserSpec

        super().perform_extra_serialization(mapping, obj, *args, **kwargs)
        if obj.geo_organization:
            mapping["geo_organization"] = OrganizationReadSpec.serialize(
                obj.geo_organization
            ).to_json()
        if obj.created_by:
            mapping["created_by"] = UserSpec.serialize(obj.created_by).to_json()
        if obj.updated_by:
            mapping["updated_by"] = UserSpec.serialize(obj.updated_by).to_json()
        if obj.instance_identifiers:
            mapping["instance_identifiers"] = [
                {
                    "config": PatientIdentifierConfigCache.get_config(x["config"]),
                    "value": x["value"],
                }
                for x in obj.instance_identifiers
            ]
        if kwargs.get("facility"):
            facility = (
                Facility.objects.only("id")
                .filter(external_id=kwargs["facility"])
                .first()
            )
            if facility:
                mapping["facility_identifiers"] = [
                    {
                        "config": PatientIdentifierConfigCache.get_config(x["config"]),
                        "value": x["value"],
                    }
                    for x in obj.facility_identifiers.get(str(facility.id), [])
                ]
