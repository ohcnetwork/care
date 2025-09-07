import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    ADMINISTRATOR,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    STAFF_ROLE,
)


class SchedulePermissions(enum.Enum):
    can_write_schedule = Permission(
        "Can Create on Schedule",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, STAFF_ROLE, FACILITY_ADMIN_ROLE, DOCTOR_ROLE, NURSE_ROLE],
    )
    can_list_schedule = Permission(
        "Can list schedule on Object",
        "",
        PermissionContext.FACILITY,
        [
            ADMIN_ROLE,
            STAFF_ROLE,
            FACILITY_ADMIN_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
        ],
    )
    can_list_booking = Permission(
        "Can list bookings on Object",
        "",
        PermissionContext.FACILITY,
        [
            ADMIN_ROLE,
            STAFF_ROLE,
            FACILITY_ADMIN_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
        ],
    )
    can_write_booking = Permission(
        "Can update bookings on Object",
        "",
        PermissionContext.FACILITY,
        [
            ADMIN_ROLE,
            STAFF_ROLE,
            FACILITY_ADMIN_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
        ],
    )
