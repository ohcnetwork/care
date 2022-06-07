from care.facility.models.mixins.permissions.base import BasePermissionMixin
from care.users.models import User


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
