import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    ADMINISTRATOR,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    PHARMACIST_ROLE,
    STAFF_ROLE,
    VOLUNTEER_ROLE,
)


class ServiceAccountPermissions(enum.Enum):
    can_create_service_account = Permission(
        "Can create service account in care",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE, ADMINISTRATOR],
    )

    can_list_service_account = Permission(
        "Can list service account in care",
        "",
        PermissionContext.FACILITY,
        [
            ADMIN_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            STAFF_ROLE,
            FACILITY_ADMIN_ROLE,
            VOLUNTEER_ROLE,
            PHARMACIST_ROLE,
        ],
    )

    can_manage_service_account = Permission(
        "Can manage service account in care",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE, ADMINISTRATOR],
    )
