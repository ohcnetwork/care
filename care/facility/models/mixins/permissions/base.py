# from care.facility.models import User
from care.users.models import User


class BasePermissionMixin:
    @staticmethod
    def has_read_permission(request):
        return request.user.is_superuser or request.user.verified

    @staticmethod
    def has_write_permission(request):
        from care.facility.models.facility import Facility

        facility = False
        try:
            facility = Facility.objects.get(external_id=request.parser_context["kwargs"]["facility_external_id"])
        except Facility.DoesNotExist:
            return False
        return (request.user.is_superuser or request.user.verified) and (
            (hasattr(facility, "created_by") and request.user == facility.created_by)
            or (
                hasattr(facility, "district")
                and request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]
                and request.user.district == facility.district
            )
            or (
                hasattr(facility, "state")
                and request.user.user_type >= User.TYPE_VALUE_MAP["StateAdmin"]
                and request.user.state == facility.state
            )
        )

    def has_object_read_permission(self, request):
        return (request.user.is_superuser or request.user.verified) and (
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
        return (request.user.is_superuser or request.user.verified) and (
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
        return request.user.is_superuser or (hasattr(self, "created_by") and request.user == self.created_by)
