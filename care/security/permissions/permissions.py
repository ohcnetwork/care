import enum
from dataclasses import dataclass


class PermissionContext(enum.Enum):
    GENERIC = "GENERIC"
    FACILITY = "FACILITY"
    ASSET = "ASSET"
    LOCATION = "LOCATION"


@dataclass
class Permission:
    """
    This class abstracts a permission
    """
    name: str
    description: str
    context: PermissionContext
    roles: list


class PermissionHandler:
    pass


from care.security.permissions.facility import FacilityPermissions  # noqa: E402


class PermissionController:
    """
    This class defines all permissions used within care.
    This class is used to abstract all operations related to permissions
    """

    override_permission_handlers = []
    # Override Permission Controllers will be defined from plugs
    internal_permission_handlers = [FacilityPermissions]

    cache = {}

    @classmethod
    def build_cache(cls):
        """
        Iterate through the entire permission library and create a list of permissions and associated Metadata
        """
        for handler in cls.internal_permission_handlers + cls.override_permission_handlers:
            for permission in handler:
                cls.cache[permission.name] = permission.value

    @classmethod
    def has_permission(cls, user, permission):
        # TODO : Cache permissions and invalidate when they change
        pass

    @classmethod
    def get_permissions(cls):
        if not cls.cache:
            cls.build_cache()
        return cls.cache
