import enum

from care.security.permissions.permissions import Permission, PermissionContext
from care.security.roles.role import STAFF_ROLE


class FacilityPermissions(enum.Enum):
    can_read_facility = Permission("Can Read on Facility", "Something Here", PermissionContext.FACILITY, [STAFF_ROLE])
    can_update_facility = Permission("Can Update on Facility", "Something Here", PermissionContext.FACILITY, [STAFF_ROLE])
