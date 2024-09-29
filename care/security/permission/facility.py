import enum

from care.security.permission.permissions import Permission, PermissionContext


class FacilityPermissions(enum.Enum):
    can_read_facility = Permission("Can Read on Facility", "", PermissionContext.FACILITY, [])
