import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    ADMINISTRATOR,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
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
        [ADMIN_ROLE],
    )
    can_manage_organization_users = Permission(
        "Can Manage Users in an Organizations",
        "",
        PermissionContext.ORGANIZATION,
        [ADMIN_ROLE, ADMINISTRATOR, FACILITY_ADMIN_ROLE],
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
        ],
    )
