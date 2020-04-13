from care.facility.models import User


class BasePermissionMixin:
    @staticmethod
    def has_read_permission(request):
        return request.user.is_superuser or request.user.verified

    @staticmethod
    def has_write_permission(request):
        return request.user.is_superuser or request.user.verified

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or request.user.verified
            or (hasattr(self, "created_by") and request.user == self.created_by)
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
        return (
            request.user.is_superuser
            or (hasattr(self, "created_by") and request.user == self.created_by)
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
