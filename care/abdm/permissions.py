from care.facility.models.mixins.permissions.base import BasePermissionMixin
from care.users.models import User


class HealthFacilityPermissions(BasePermissionMixin):
    """
    Permissions for HealthFacilityViewSet
    """

    def has_object_read_permission(self, request):
        return self.facility.has_object_read_permission(request)

    def has_object_write_permission(self, request):
        allowed_user_types = [
            User.TYPE_VALUE_MAP["WardAdmin"],
            User.TYPE_VALUE_MAP["LocalBodyAdmin"],
            User.TYPE_VALUE_MAP["DistrictAdmin"],
            User.TYPE_VALUE_MAP["StateAdmin"],
        ]
        return request.user.is_superuser or (
            request.user.user_type in allowed_user_types
            and self.facility.has_object_write_permission(request)
        )

    def has_object_update_permission(self, request):
        return self.has_object_write_permission(request)

    def has_object_destroy_permission(self, request):
        return self.has_object_write_permission(request)
