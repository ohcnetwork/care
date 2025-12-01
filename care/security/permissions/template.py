import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import ADMIN_ROLE, FACILITY_ADMIN_ROLE


class TemplatePermissions(enum.Enum):
    can_write_template = Permission(
        "Can Create Template on Facility",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )
    can_read_template = Permission(
        "Can Read Template",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )
    can_preview_template = Permission(
        "Can Preview Template",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )
    can_view_template_schema = Permission(
        "Can View Template Schema",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )
