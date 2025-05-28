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


class UserSchedulePermissions(enum.Enum):
    can_write_user_schedule = Permission(
        "Can Create on User Schedule",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, STAFF_ROLE, FACILITY_ADMIN_ROLE, DOCTOR_ROLE, NURSE_ROLE],
    )
    can_list_user_schedule = Permission(
        "Can list user schedule on Facility",
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
    can_list_user_booking = Permission(
        "Can list bookings on Facility",
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
    can_write_user_booking = Permission(
        "Can update bookings on user",
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
    can_create_appointment = Permission(
        "Can create appointment on facility",
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
    can_reschedule_appointment = Permission(
        "Can reschedule appointment on facility",
        "",
        PermissionContext.FACILITY,
        [
            DOCTOR_ROLE,
            STAFF_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            FACILITY_ADMIN_ROLE,
            ADMIN_ROLE,
        ],
    )
