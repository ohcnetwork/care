import re
from enum import Enum
from typing import Any, Literal

import pycountry
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pydantic import UUID4, BaseModel, Field, field_validator

from care.emr.models import Organization
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.resources.base import EMRResource, cacheable, model_from_cache
from care.emr.resources.patient.spec import GenderChoices
from care.facility.models.facility import Facility
from care.security.models import RolePermission
from care.users.models import User
from care.utils.shortcuts import get_object_or_404


def is_valid_username(username):
    pattern = r"^[a-zA-Z0-9_-]{3,}$"
    return bool(re.fullmatch(pattern, username))


class UserLanguageSpec(BaseModel):
    code: str = Field(pattern=r"^[a-z]{3}$")
    system: Literal["urn:iso:std:iso:639:-3"]

    @field_validator("code")
    @classmethod
    def validate_language_code(cls, code):
        if pycountry.languages.get(alpha_3=code) is None:
            raise ValueError("Invalid ISO 639-3 language code")
        return code


class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class UserCommunicationSpec(BaseModel):
    language: UserLanguageSpec
    preferred: bool
    proficiency: CEFRLevel | None = None


class UserDegreeSpec(BaseModel):
    code: str = Field(min_length=1)
    system: str = Field(min_length=1)


class UserQualificationSpec(BaseModel):
    registration_number: str
    issuer: str
    degree: UserDegreeSpec
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("degree")
    @classmethod
    def validate_degree(cls, degree):
        if not any(
            degree.code == available_degree["code"]
            and degree.system == available_degree["system"]
            for available_degree in settings.USER_QUALIFICATION_DEGREES
        ):
            raise ValueError("Degree must be one of the available qualifications")
        return degree


class UserBaseSpec(EMRResource):
    __model__ = User
    __exclude__ = ["geo_organization"]

    id: UUID4 | None = None

    first_name: str
    last_name: str
    phone_number: str = Field(max_length=14)

    prefix: str | None = Field(None, max_length=10)
    suffix: str | None = Field(None, max_length=50)


class UserUpdateSpec(UserBaseSpec):
    gender: GenderChoices
    phone_number: str = Field(max_length=14)
    geo_organization: UUID4 | None = None
    communication: list[UserCommunicationSpec] = Field(default_factory=list)
    qualification: list[UserQualificationSpec] = Field(default_factory=list)

    def perform_extra_deserialization(self, is_update, obj):
        if "communication" in self.model_fields_set:
            obj.communication = [
                communication.model_dump(mode="json")
                for communication in self.communication
            ]
        if "qualification" in self.model_fields_set:
            obj.qualifications = [
                qualification.model_dump(mode="json")
                for qualification in self.qualification
            ]
        if self.geo_organization is not None:
            obj.geo_organization = get_object_or_404(
                Organization, external_id=self.geo_organization, org_type="govt"
            )


class UserRoleOrgCreateSpec(BaseModel):
    organization: UUID4
    role: UUID4


class UserCreateSpec(UserUpdateSpec):
    password: str | None = None
    username: str
    email: str
    is_service_account: bool = False
    role_orgs: list[UserRoleOrgCreateSpec]

    @field_validator("username")
    @classmethod
    def validate_username(cls, username):
        if not is_valid_username(username):
            raise ValueError(
                "Username can only contain alpha numeric values, dashes ( - ) and underscores ( _ )"
            )
        if User.check_username_exists(username):
            raise ValueError("Username already exists")
        return username

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, phone_number):
        if User.objects.filter(phone_number=phone_number).exists():
            raise ValueError("Phone Number already exists")
        return phone_number

    @field_validator("email")
    @classmethod
    def validate_user_email(cls, email):
        if User.objects.filter(email=email).exists():
            raise ValueError("Email already exists")
        try:
            validate_email(email)
        except ValidationError as e:
            raise ValueError("Invalid Email") from e
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, password):
        if password is None:
            return None
        try:
            validate_password(password)
        except Exception as e:
            raise ValueError("Password is too weak") from e
        return password

    def perform_extra_deserialization(self, is_update, obj):
        super().perform_extra_deserialization(is_update, obj)
        obj._role_orgs = self.role_orgs  # noqa SLF001
        obj.set_password(self.password)


@cacheable(use_base_manager=True)
class UserSpec(UserBaseSpec):
    last_login: str
    profile_picture_url: str
    gender: str
    username: str
    mfa_enabled: bool = False
    phone_number: str = Field(max_length=14)
    deleted: bool = False
    role_orgs: dict
    communication: list[UserCommunicationSpec] = Field(default_factory=list)
    qualification: list[UserQualificationSpec] = Field(default_factory=list)

    @classmethod
    def perform_extra_serialization(cls, mapping, obj: User):
        super().perform_extra_serialization(mapping, obj)
        mapping["id"] = str(obj.external_id)
        mapping["profile_picture_url"] = obj.read_profile_picture_url()
        mapping["mfa_enabled"] = obj.is_mfa_enabled()
        mapping["role_orgs"] = obj.get_cached_role_orgs()
        mapping["qualification"] = obj.qualifications


class UserRetrieveSpec(UserSpec):
    geo_organization: dict
    created_by: dict | None = None
    email: str
    flags: list[str] = []
    is_service_account: bool

    @classmethod
    def perform_extra_serialization(cls, mapping, obj: User):
        from care.emr.resources.organization.spec import OrganizationReadSpec

        super().perform_extra_serialization(mapping, obj)
        if obj.created_by_id:
            mapping["created_by"] = model_from_cache(UserSpec, id=obj.created_by_id)
        if obj.geo_organization:
            mapping["geo_organization"] = OrganizationReadSpec.serialize(
                obj.geo_organization
            ).to_json()
        mapping["flags"] = obj.get_all_flags()


class CurrentUserRetrieveSpec(UserRetrieveSpec):
    is_superuser: bool
    alt_phone_number: str | None
    date_of_birth: str | None
    pf_endpoint: str | None
    pf_p256dh: str | None
    pf_auth: str | None
    organizations: list[dict]
    facilities: list[dict]
    permissions: list[str]
    preferences: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj: User) -> None:
        from care.emr.resources.facility.spec import FacilityBareMinimumSpec
        from care.emr.resources.organization.spec import OrganizationReadSpec

        super().perform_extra_serialization(mapping, obj)

        if obj.is_superuser:
            organizations = Organization.objects.filter(parent__isnull=True)
        else:
            organizations = Organization.objects.filter(
                id__in=OrganizationUser.objects.filter(user=obj).values_list(
                    "organization_id", flat=True
                )
            )
        mapping["organizations"] = [
            OrganizationReadSpec.serialize(obj).to_json() for obj in organizations
        ]

        user_facilities = Facility.objects.filter(
            id__in=FacilityOrganizationUser.objects.filter(
                user=obj, organization__facility__deleted=False
            ).values_list("organization__facility_id", flat=True)
        )
        mapping["facilities"] = [
            FacilityBareMinimumSpec.serialize(obj).to_json() for obj in user_facilities
        ]

        mapping["permissions"] = list(
            RolePermission.objects.filter(
                role_id__in=OrganizationUser.objects.filter(user=obj).values_list(
                    "role_id", flat=True
                )
            )
            .select_related("permission")
            .values_list("permission__slug", flat=True)
        )


class PublicUserReadSpec(UserBaseSpec):
    last_login: str
    profile_picture_url: str
    gender: str
    username: str
    role_orgs: list[dict]

    @classmethod
    def perform_extra_serialization(cls, mapping, obj: User):
        mapping["id"] = str(obj.external_id)
        mapping["profile_picture_url"] = obj.read_profile_picture_url()
        mapping["role_orgs"] = obj.get_cached_role_orgs()


class ResetPasswordCheckRequest(BaseModel):
    token: str


class ResetPasswordConfirmRequest(BaseModel):
    token: str
    password: str


class ResetPasswordResponse(BaseModel):
    detail: str


class ResetPasswordRequestTokenRequest(BaseModel):
    username: str
