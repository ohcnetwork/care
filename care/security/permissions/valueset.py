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


class ValueSetPermissions(enum.Enum):
    can_write_valueset = Permission(
        "Can Create/Update ValueSets",
        "",
        PermissionContext.GENERIC,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_read_valueset = Permission(
        "Can Read ValueSets",
        "",
        PermissionContext.GENERIC,
        [
            ADMIN_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            STAFF_ROLE,
            FACILITY_ADMIN_ROLE,
            VOLUNTEER_ROLE,
            PHARMACIST_ROLE,
            ROLE_ORGANIZATION_ADMIN_ROLE,
            ROLE_ORGANIZATION_MANAGER_ROLE,
            ROLE_ORGANIZATION_MEMBER_ROLE,
        ],
    )
