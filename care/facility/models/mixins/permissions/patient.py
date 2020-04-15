from care.facility.models import User
from care.facility.models.mixins.permissions.base import BasePermissionMixin


class PatientPermissionMixin(BasePermissionMixin):
    @staticmethod
    def has_write_permission(request):
        return (
            request.user.is_superuser
            or request.user.verified
            and request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]
        )

    def has_object_read_permission(self, request):
        return request.user.is_superuser or (
            super().has_object_read_permission(request)
            and (
                (hasattr(self, "created_by") and request.user == self.created_by)
                or (self.facility and self.facility.users.filter(user=request.user).exists())
                or (
                    request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                    and (
                        request.user.district == self.district
                        or (self.facility and request.user.district == self.facility.district)
                    )
                )
                or (
                    request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                    and (
                        request.user.state == self.state
                        or (self.facility and request.user.state == self.facility.district)
                    )
                )
            )
        )

    def has_object_update_permission(self, request):
        return request.user.is_superuser or (
            super().has_object_update_permission(request)
            and (
                (hasattr(self, "created_by") and request.user == self.created_by)
                or (self.facility and self.facility.users.filter(user=request.user).exists())
                or (
                    request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                    and (
                        request.user.district == self.district
                        or (self.facility and request.user.district == self.facility.district)
                    )
                )
                or (
                    request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                    and (
                        request.user.state == self.state
                        or (self.facility and request.user.state == self.facility.district)
                    )
                )
            )
        )


class PatientRelatedPermissionMixin(BasePermissionMixin):
    @staticmethod
    def has_write_permission(request):
        return super().has_write_permission(request) and request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]

    def has_object_read_permission(self, request):
        return super().has_object_read_permission(request) and (
            (self.patient.facility and self.patient.facility.users.filter(user=request.user).exists())
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    request.user.district == self.district
                    or (self.patient.facility and request.user.district == self.patient.facility.district)
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    request.user.state == self.state
                    or (self.patient.facility and request.user.state == self.patient.facility.district)
                )
            )
        )

    def has_object_update_permission(self, request):
        return super().has_object_read_permission(request) and (
            (self.patient.facility and self.patient.facility.users.filter(user=request.user).exists())
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    request.user.district == self.district
                    or (self.patient.facility and request.user.district == self.patient.facility.district)
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    request.user.state == self.state
                    or (self.patient.facility and request.user.state == self.patient.facility.district)
                )
            )
        )
