from care.facility.models.mixins.permissions.base import BasePermissionMixin
from care.users.models import User


class FacilityPermissionMixin(BasePermissionMixin):
    @staticmethod
    def has_bulk_upsert_permission(request):
        return request.user.is_superuser

    @staticmethod
    def has_write_permission(request):
        from care.users.models import State, District, LocalBody

        try:
            state = State.objects.get(id=request.data["state"])
            district = District.objects.get(id=request.data["district"])
            return (
                request.user.is_superuser
                or (
                    request.user.user_type > User.TYPE_VALUE_MAP["DistrictAdmin"]
                    and state == request.user.state
                )
                or (
                    request.user.user_type > User.TYPE_VALUE_MAP["LocalBodyAdmin"]
                    and state == request.user.state
                    and district == request.user.district
                )
            )
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def has_destroy_permission(request):
        from care.facility.models import Facility

        try:
            facility = Facility.objects.get(
                external_id=request.parser_context["kwargs"]["external_id"]
            )
            return (
                request.user.is_superuser
                or (
                    request.user.user_type > User.TYPE_VALUE_MAP["DistrictAdmin"]
                    and facility.state == request.user.state
                )
                or (
                    request.user.user_type > User.TYPE_VALUE_MAP["LocalBodyAdmin"]
                    and facility.state == request.user.state
                    and facility.district == request.user.district
                )
            )
        except Exception as e:
            print(e)
            return False

    def has_object_read_permission(self, request):
        return (
            (request.user.is_superuser)
            or (
                hasattr(self, "district")
                and request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district == self.district
            )
            or (
                hasattr(self, "state")
                and request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and request.user.state == self.state
            )
            or (request.user in self.users.all())
        )

    def has_object_write_permission(self, request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False
        if request.user.user_type < User.TYPE_VALUE_MAP["Staff"]:  # todo Temporary
            return False
        return self.has_object_read_permission(request)

    def has_object_update_permission(self, request):
        return super().has_object_update_permission(
            request
        ) or self.has_object_write_permission(request)

    def has_object_destroy_permission(self, request):
        return self.has_object_read_permission(request)


class FacilityRelatedPermissionMixin(BasePermissionMixin):
    @staticmethod
    def has_write_permission(request):
        from care.facility.models.facility import Facility

        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False

        facility = False
        try:
            facility = Facility.objects.get(
                external_id=request.parser_context["kwargs"]["facility_external_id"]
            )
        except Facility.DoesNotExist:
            return False
        return (request.user.is_superuser or request.user.verified) and (
            (hasattr(facility, "created_by") and request.user == facility.created_by)
            or (
                hasattr(facility, "district")
                and request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district == facility.district
            )
            or (
                hasattr(facility, "state")
                and request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and request.user.state == facility.state
            )
            or (request.user in facility.users.all())
        )

    def has_object_read_permission(self, request):
        return (
            super().has_object_read_permission(request)
            or request.user.is_superuser
            or request.user in self.facility.users.all()
        )

    def has_object_write_permission(self, request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False
        return (
            super().has_write_permission(request)
            or request.user.is_superuser
            or request.user in self.facility.users.all()
        )
