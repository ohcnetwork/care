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


class FacilityOrganizationPermissions(enum.Enum):
    can_create_facility_organization = Permission(
        "Can Create Facility Organizations",
        "",
        PermissionContext.FACILITY_ORGANIZATION,
        [FACILITY_ADMIN_ROLE],
    )
    can_create_facility_organization_root = Permission(
        "Can Create Facility Organizations Root",
        "",
        PermissionContext.FACILITY_ORGANIZATION,
        [FACILITY_ADMIN_ROLE],
    )
    can_view_facility_organization = Permission(
        "Can View Facility Organizations",
        "",
        PermissionContext.FACILITY_ORGANIZATION,
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
    can_delete_facility_organization = Permission(
        "Can Delete Facility Organizations",
        "",
        PermissionContext.FACILITY_ORGANIZATION,
        [FACILITY_ADMIN_ROLE],
    )
    can_manage_facility_organization = Permission(
        "Can Manage Facility Organizations",
        "This includes changing names, descriptions, metadata, etc..",
        PermissionContext.FACILITY_ORGANIZATION,
        [FACILITY_ADMIN_ROLE, ADMINISTRATOR],
    )
    can_list_facility_organization_users = Permission(
        "Can List Users in a Facility Organizations",
        "",
        PermissionContext.FACILITY_ORGANIZATION,
        [
            FACILITY_ADMIN_ROLE,
            ADMIN_ROLE,
            STAFF_ROLE,
            DOCTOR_ROLE,
            ADMINISTRATOR,
            NURSE_ROLE,
        ],
    )
    can_manage_facility_organization_users = Permission(
        "Can Manage Users in an Organizations",
        "",
        PermissionContext.FACILITY_ORGANIZATION,
        [FACILITY_ADMIN_ROLE, ADMINISTRATOR],
    )
