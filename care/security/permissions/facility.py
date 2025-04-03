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


class FacilityPermissions(enum.Enum):
    can_create_facility = Permission(
        "Can Create on Facility",
        "Something Here",
        PermissionContext.FACILITY,
        [ADMINISTRATOR, ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_read_facility = Permission(
        "Can Read on Facility",
        "Something Here",
        PermissionContext.FACILITY,
        [
            FACILITY_ADMIN_ROLE,
            ADMINISTRATOR,
            ADMIN_ROLE,
            STAFF_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            VOLUNTEER_ROLE,
        ],
    )
    can_update_facility = Permission(
        "Can Update on Facility",
        "Something Here",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMINISTRATOR, ADMIN_ROLE, STAFF_ROLE],
    )
