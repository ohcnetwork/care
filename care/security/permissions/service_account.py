import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import ADMIN_ROLE, ADMINISTRATOR, FACILITY_ADMIN_ROLE


class ServiceAccountPermissions(enum.Enum):
    can_create_service_account = Permission(
        "Can create service account in care",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE, ADMINISTRATOR],
    )
