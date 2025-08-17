import re
from enum import Enum

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pydantic import UUID4, Field, field_validator
from rest_framework.generics import get_object_or_404

from care.emr.models import Organization
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.resources.base import EMRResource, cacheable, model_from_cache
from care.emr.resources.patient.spec import GenderChoices
from care.facility.models.facility import Facility
from care.security.models import RolePermission
from care.security.roles.role import (
    ADMINISTRATOR,
    DOCTOR_ROLE,
    NURSE_ROLE,
    STAFF_ROLE,
    VOLUNTEER_ROLE,
)
from care.users.models import User


def is_valid_username(username):
    pattern = r"^[a-zA-Z0-9_-]{3,}$"
    return bool(re.fullmatch(pattern, username))


class UserTypeOptions(str, Enum):
    doctor = "doctor"
    nurse = "nurse"
    staff = "staff"
    volunteer = "volunteer"
    administrator = "administrator"


class UserTypeRoleMapping(Enum):
    doctor = DOCTOR_ROLE
    nurse = NURSE_ROLE
    staff = STAFF_ROLE
    volunteer = VOLUNTEER_ROLE
    administrator = ADMINISTRATOR


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
    user_type: UserTypeOptions
    gender: GenderChoices
    phone_number: str = Field(max_length=14)
    geo_organization: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.geo_organization is not None:
            obj.geo_organization = get_object_or_404(
                Organization, external_id=self.geo_organization, org_type="govt"
            )


class UserCreateSpec(UserUpdateSpec):
    password: str | None = None
    username: str
    email: str

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
        obj.set_password(self.password)


@cacheable(use_base_manager=True)
class UserSpec(UserBaseSpec):
    last_login: str
    profile_picture_url: str
    user_type: str
    gender: str
    username: str
    mfa_enabled: bool = False
    phone_number: str = Field(max_length=14)
    deleted: bool = False

    @classmethod
    def perform_extra_serialization(cls, mapping, obj: User):
        mapping["id"] = str(obj.external_id)
        mapping["profile_picture_url"] = obj.read_profile_picture_url()
        mapping["mfa_enabled"] = obj.is_mfa_enabled()


class UserRetrieveSpec(UserSpec):
    geo_organization: dict
    created_by: UserSpec
    email: str
    flags: list[str] = []

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
    qualification: str | None
    doctor_experience_commenced_on: str | None
    doctor_medical_council_registration: str | None
    weekly_working_hours: str | None
    alt_phone_number: str | None
    date_of_birth: str | None
    verified: bool
    pf_endpoint: str | None
    pf_p256dh: str | None
    pf_auth: str | None
    organizations: list[dict]
    facilities: list[dict]
    permissions: list[str]

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

        mapping["permissions"] = (
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
    user_type: str
    gender: str
    username: str

    @classmethod
    def perform_extra_serialization(cls, mapping, obj: User):
        mapping["id"] = str(obj.external_id)
        mapping["profile_picture_url"] = obj.read_profile_picture_url()
