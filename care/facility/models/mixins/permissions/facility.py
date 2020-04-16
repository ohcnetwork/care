from care.facility.models.mixins.permissions.base import BasePermissionMixin


class FacilityPermissionMixin(BasePermissionMixin):
    @staticmethod
    def has_bulk_upsert_permission(request):
        return request.user.is_superuser

    def has_object_read_permission(self, request):
        return super().has_object_read_permission(request) or request.user in self.users.all()

    def has_object_write_permission(self, request):
        return super().has_write_permission(request) or request.user in self.users.all()


class FacilityRelatedPermissionMixin(BasePermissionMixin):
    def has_object_read_permission(self, request):
        return super().has_object_read_permission(request) or request.user in self.facility.users.all()

    def has_object_write_permission(self, request):
        return super().has_write_permission(request) or request.user in self.facility.users.all()
