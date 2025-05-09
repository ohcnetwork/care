import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    FACILITY_ADMIN_ROLE,
)


class TemplatePermissions(enum.Enum):
    can_list_template = Permission(
        "Can List Templates in Facility",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_manage_template = Permission(
        "Can Write/Update/Delete Templates in Facility",
        "",
        PermissionContext.FACILITY,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
