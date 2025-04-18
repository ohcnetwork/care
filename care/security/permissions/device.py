import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    STAFF_ROLE,
)


class DevicePermissions(enum.Enum):
    can_list_devices = Permission(
        "Can List Devices on Facility",
        "",
        PermissionContext.FACILITY,
        [STAFF_ROLE, ADMIN_ROLE, DOCTOR_ROLE, NURSE_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_manage_device_associations_to_encounters = Permission(
        "Can Manage Device Associations to Encounters",
        "",
        PermissionContext.FACILITY,
        [STAFF_ROLE, ADMIN_ROLE, DOCTOR_ROLE, NURSE_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_manage_devices = Permission(
        "Can Manage Devices on Facility",
        "",
        PermissionContext.FACILITY,
        [STAFF_ROLE, ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
