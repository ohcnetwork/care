import enum
from dataclasses import dataclass

from care.security.models import RoleAssociation, RolePermission


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
        for handler in (
            cls.internal_permission_handlers + cls.override_permission_handlers
        ):
            for permission in handler:
                cls.cache[permission.name] = permission.value

    @classmethod
    def has_permission(cls, user, permission, context, context_id):
        # TODO : Cache permissions and invalidate when they change
        # TODO : Fetch the user role from the previous role management implementation as well.
        #        Need to maintain some sort of mapping from previous generation to new generation of roles
        from care.security.roles.role import RoleController

        mapped_role = RoleController.map_old_role_to_new(user.role)
        permission_roles = RolePermission.objects.filter(
            permission__slug=permission, permission__context=context
        ).values("role_id")
        if RoleAssociation.objects.filter(
            context_id=context_id, context=context, role__in=permission_roles, user=user
        ).exists():
            return True
        # Check for old cases
        return RolePermission.objects.filter(
            permission__slug=permission,
            permission__context=context,
            role__name=mapped_role.name,
            role__context=mapped_role.context.value,
        ).exists()

    @classmethod
    def get_permissions(cls):
        if not cls.cache:
            cls.build_cache()
        return cls.cache
