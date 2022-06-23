from dry_rest_permissions.generics import DRYPermissions

from care.facility.models.mixins.permissions.base import BasePermissionMixin
from care.users.models import User


class IsAssetUser:
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.asset
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class DRYAssetPermissions(DRYPermissions):
    """
    Adds additional prefix for asset users to the permission names.
    """

    global_permissions = False

    def _get_action(self, action):
        return f"asset_{super()._get_action(action)}"


class AssetsPermissionMixin(BasePermissionMixin):
    def has_object_read_permission(self, request):
        return True

    def has_object_write_permission(self, request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False

        return True

    def has_object_update_permission(self, request):
        return self.has_object_write_permission(request)

    def has_object_destroy_permission(self, request):
        return self.has_object_write_permission(request)
