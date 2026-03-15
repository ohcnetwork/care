import secrets
import uuid

from care.emr.models import Organization
from care.emr.resources.organization.spec import OrganizationTypeChoices
from care.emr.resources.patient.spec import GenderChoices
from care.emr.resources.user.spec import UserCreateSpec
from care.security.models import RoleModel
from care.users.models import User

from . import ROLES_OPTIONS, generate_unique_indian_phone_number
from .organizations import (
    attach_role_facility_organization_user,
    attach_role_organization_user,
)


def create_user(
    fake,
    username,
    user_type,
    super_user,
    geo_organization,
    facility_organization=None,
    role=None,
    password=None,
):
    password = password or fake.password(length=10, special_chars=False)
    user_spec = UserCreateSpec(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        phone_number=generate_unique_indian_phone_number(),
        prefix=fake.prefix(),
        suffix=fake.suffix(),
        gender=secrets.choice(list(GenderChoices)).value,
        password=password,
        username=username,
        email=str(uuid.uuid4()) + fake.email(),
        user_type=user_type,
    )
    user = user_spec.de_serialize()
    user.geo_organization = geo_organization
    user.created_by = super_user
    user.updated_by = super_user
    user.save()

    if role:
        if facility_organization:
            attach_role_facility_organization_user(
                facility_organization=facility_organization,
                user=user,
                role=role,
            )
            if (
                user.user_type == "administrator"
                and facility_organization.facility.default_internal_organization
            ):
                attach_role_facility_organization_user(
                    facility_organization=facility_organization.facility.default_internal_organization,
                    user=user,
                    role=role,
                )
        if user.geo_organization:
            attach_role_organization_user(
                organization=user.geo_organization,
                user=user,
                role=role,
            )
        attach_role_organization_user(
            organization=Organization.objects.get(
                name=role.name, org_type=OrganizationTypeChoices.role
            ),
            user=user,
            role=role,
        )

    return user, password


def create_default_users(fake, super_user, facility_organization, geo_organization):
    fixed_users = [
        ("Doctor", "care-doctor"),
        ("Staff", "care-staff"),
        ("Nurse", "care-nurse"),
        ("Administrator", "care-admin"),
        ("Volunteer", "care-volunteer"),
        ("Facility Admin", "care-fac-admin"),
    ]

    password = "Ohcn@123"
    created_users = []
    for role_name, username in fixed_users:
        try:
            role = RoleModel.objects.get(name=role_name)

            if User.objects.filter(username=username).exists():
                continue

            _user, _ = create_user(
                fake,
                username=username,
                user_type=ROLES_OPTIONS[role_name],
                super_user=super_user,
                geo_organization=geo_organization,
                facility_organization=facility_organization,
                role=role,
                password=password,
            )
            created_users.append(
                {"username": username, "password": password, "role": role_name}
            )
        except RoleModel.DoesNotExist:
            pass

    return created_users


def create_facility_users(
    fake,
    super_user,
    facility_organization,
    geo_organization,
    count,
    default_password=None,
):
    created_users = []
    for role_name, user_type in ROLES_OPTIONS.items():
        try:
            role = RoleModel.objects.get(name=role_name)

            for i in range(count):
                password = default_password or fake.password(
                    length=10, special_chars=False
                )
                username = (
                    f"{role_name.lower()}_{facility_organization.id}_{i}".replace(
                        " ", "_"
                    )
                )

                create_user(
                    fake,
                    username=username,
                    user_type=user_type,
                    super_user=super_user,
                    geo_organization=geo_organization,
                    facility_organization=facility_organization,
                    role=role,
                    password=password,
                )
                created_users.append(
                    {"username": username, "password": password, "role": role_name}
                )
        except RoleModel.DoesNotExist:
            pass

    return created_users


def setup_admin(ctx):
    """Create the superuser account.

    Populates ctx.super_user and ctx.manifest["admin"].
    """
    super_user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "user_type": "admin",
            "is_superuser": True,
            "is_staff": True,
            "first_name": "Admin",
            "last_name": "User",
        },
    )
    if created:
        super_user.set_password("admin")
        super_user.save()

    ctx.super_user = super_user
    ctx.log("=" * 30)
    if created:
        ctx.log("Superuser username: admin")
        ctx.log("Superuser password: admin")
    else:
        ctx.log("Superuser 'admin' already exists, not creating a new one.")
    ctx.log("=" * 30)

    ctx.manifest["admin"] = {"username": "admin", "password": "admin"}


def setup_users(ctx):
    """Create default and facility users.

    Populates ctx.manifest["users"].
    """
    # Default users (fixed credentials for manual testing)
    default_users = create_default_users(
        ctx.fake, ctx.super_user, ctx.facility_organization, ctx.geo_organization
    )

    ctx.log("=" * 50)
    ctx.log("DEFAULT USER CREDENTIALS")
    ctx.log("=" * 50)
    for u in default_users:
        ctx.log(f"{u['role']:<15} {u['username']:<30} {u['password']:<20}")
    ctx.log("=" * 50)

    # Facility users (generated per role x count)
    ctx.log("=" * 50)
    ctx.log("USER CREDENTIALS")
    ctx.log("=" * 50)
    ctx.log(f"{'ROLE':<15} {'USERNAME':<30} {'PASSWORD':<20}")
    ctx.log("-" * 65)

    facility_users = create_facility_users(
        ctx.fake,
        ctx.super_user,
        ctx.facility_organization,
        ctx.geo_organization,
        ctx.options["users"],
        ctx.options["default_password"],
    )
    for u in facility_users:
        ctx.log(f"{u['role']:<15} {u['username']:<30} {u['password']:<20}")
    ctx.log("=" * 50)

    ctx.manifest["users"] = default_users + facility_users
