from care.users.models import User


class BasePermissionMixin:
    @staticmethod
    def has_read_permission(request):
        return request.user.is_superuser or request.user.verified

    @staticmethod
    def has_write_permission(request):
        if request.user.user_type in User.READ_ONLY_TYPES:
            return False
        return (
            request.user.is_superuser
            or request.user.verified
            or request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]
        )

    def has_object_read_permission(self, request):
        return (request.user.is_superuser) or (
            (hasattr(self, "created_by") and request.user == self.created_by)
            or (
                hasattr(self, "district")
                and request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]
                and request.user.district == self.district
            )
            or (
                hasattr(self, "state")
                and request.user.user_type >= User.TYPE_VALUE_MAP["StateAdmin"]
                and request.user.state == self.state
            )
        )

    def has_object_update_permission(self, request):
        if request.user.user_type in User.READ_ONLY_TYPES:
            return False
        return (request.user.is_superuser) or (
            (hasattr(self, "created_by") and request.user == self.created_by)
            or (
                hasattr(self, "district")
                and request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]
                and request.user.district == self.district
            )
            or (
                hasattr(self, "state")
                and request.user.user_type >= User.TYPE_VALUE_MAP["StateAdmin"]
                and request.user.state == self.state
            )
        )

    def has_object_destroy_permission(self, request):
        if request.user.user_type in User.READ_ONLY_TYPES:
            return False
        return request.user.is_superuser or (
            hasattr(self, "created_by") and request.user == self.created_by
        )
