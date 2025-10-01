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


class TokenPermissions(enum.Enum):
    can_write_token_category = Permission(
        "Can Create on Token Category",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, STAFF_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_list_token_category = Permission(
        "Can list token category on Facility",
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
    can_write_token = Permission(
        "Can Create on Token",
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
    can_list_token = Permission(
        "Can list token on Object",
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
