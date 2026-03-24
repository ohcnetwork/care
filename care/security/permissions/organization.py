import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    ADMINISTRATOR,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    PHARMACIST_ROLE,
    ROLE_ORGANIZATION_ADMIN_ROLE,
    ROLE_ORGANIZATION_MANAGER_ROLE,
    ROLE_ORGANIZATION_MEMBER_ROLE,
    STAFF_ROLE,
    VOLUNTEER_ROLE,
)


class OrganizationPermissions(enum.Enum):
    can_view_organization = Permission(
        "Can View Organizations",
        "",
        PermissionContext.ORGANIZATION,
        [
            FACILITY_ADMIN_ROLE,
            ADMIN_ROLE,
            STAFF_ROLE,
            DOCTOR_ROLE,
            ADMINISTRATOR,
            NURSE_ROLE,
            VOLUNTEER_ROLE,
            PHARMACIST_ROLE,
            ROLE_ORGANIZATION_ADMIN_ROLE,
            ROLE_ORGANIZATION_MANAGER_ROLE,
            ROLE_ORGANIZATION_MEMBER_ROLE,
        ],
    )
    can_create_organization = Permission(
        "Can Create Organizations",
        "",
        PermissionContext.ORGANIZATION,
        [ADMIN_ROLE],
    )
    can_delete_organization = Permission(
        "Can Delete Organizations",
        "",
        PermissionContext.ORGANIZATION,
        [ADMIN_ROLE],
    )
    can_manage_organization = Permission(
        "Can Manage Organizations",
        "This includes changing names, descriptions, metadata, etc..",
        PermissionContext.ORGANIZATION,
        [ADMIN_ROLE, ROLE_ORGANIZATION_ADMIN_ROLE],
    )
    can_manage_organization_users = Permission(
        "Can Manage Users in an Organization",
        "Add, remove, and assign roles to users in an organization",
        PermissionContext.ORGANIZATION,
        [ADMIN_ROLE, ADMINISTRATOR, FACILITY_ADMIN_ROLE, ROLE_ORGANIZATION_ADMIN_ROLE],
    )
    can_manage_connected_role_organizations = Permission(
        "Can Manage Connected Role Organizations",
        "Add, remove, and assign roles to users in connected role organizations",
        PermissionContext.ORGANIZATION,
        [ROLE_ORGANIZATION_ADMIN_ROLE, ROLE_ORGANIZATION_MANAGER_ROLE],
    )
    can_list_organization_users = Permission(
        "Can List Users in an Organizations",
        "",
        PermissionContext.ORGANIZATION,
        [
            FACILITY_ADMIN_ROLE,
            ADMIN_ROLE,
            STAFF_ROLE,
            DOCTOR_ROLE,
            ADMINISTRATOR,
            NURSE_ROLE,
            VOLUNTEER_ROLE,
            PHARMACIST_ROLE,
            ROLE_ORGANIZATION_ADMIN_ROLE,
            ROLE_ORGANIZATION_MANAGER_ROLE,
        ],
    )
    is_geo_admin = Permission(
        "Is Geo Admin",
        "Geo Admins can manage facilities in their organization",
        PermissionContext.ORGANIZATION,
        [],
    )
