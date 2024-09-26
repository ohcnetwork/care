import enum
from dataclasses import dataclass


class PermissionContext(enum.Enum):
    GENERIC = "GENERIC"
    FACILITY = "FACILITY"
    ASSET = "ASSET"


@dataclass
class Permission:
    """
    This class abstracts a permission
    """
    permission_name: str
    permission_description: str
    permission_context: PermissionContext
    roles: list


class InternalPermissionController:
    pass


class ExternalPermissionController:
    pass


class PermissionController:
    """
    This class defines all permissions used within care.
    This class is used to abstract all operations related to permissions
    """

    OVERRIDE_PERMISSION_CONTROLLERS = []
    # Override Permission Controllers will be defined from plugs
    INTERNAL_PERMISSION_CONTROLLERS = []
