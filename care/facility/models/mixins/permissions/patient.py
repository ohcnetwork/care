from care.facility.models import Facility, User
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
            (hasattr(self, "created_by") and request.user == self.created_by)
            or (self.facility and request.user in self.facility.users.all())
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
                    request.user.state == self.state or (self.facility and request.user.state == self.facility.district)
                )
            )
        )

    def has_object_write_permission(self, request):
        return request.user.is_superuser or (
            (hasattr(self, "created_by") and request.user == self.created_by)
            or (self.facility and request.user in self.facility.users.all())
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
                    request.user.state == self.state or (self.facility and request.user.state == self.facility.district)
                )
            )
        )

    def has_object_update_permission(self, request):
        return (
            request.user.is_superuser
            or (hasattr(self, "created_by") and request.user == self.created_by)
            or (self.facility and request.user in self.facility.users.all())
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
                    request.user.state == self.state or (self.facility and request.user.state == self.facility.district)
                )
            )
        )

    def has_object_icmr_sample_permission(self, request):
        return self.has_object_read_permission(request)

    def has_object_transfer_permission(self, request):
        new_facility = Facility.objects.filter(id=request.data.get("facility", None)).first()
        return self.has_object_update_permission(request) or (new_facility and request.user in new_facility.users.all())


class PatientRelatedPermissionMixin(BasePermissionMixin):
    @staticmethod
    def has_write_permission(request):
        return (
            request.user.is_superuser
            or request.user.verified
            and request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]
        )

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or (self.patient.facility and request.user in self.patient.facility.users.all())
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (self.patient.facility and request.user.district == self.patient.facility.district)
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (self.patient.facility and request.user.state == self.patient.facility.district)
            )
        )

    def has_object_update_permission(self, request):
        return self.has_object_read_permission(request)
