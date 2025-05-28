from django.db import transaction
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.resources.role.spec import (
    RoleCreateSpec,
    RoleReadSpec,
)
from care.security.models import PermissionModel, RoleModel, RolePermission


class RoleViewSet(EMRModelViewSet):
    database_model = RoleModel
    pydantic_model = RoleCreateSpec
    pydantic_read_model = RoleReadSpec

    def permissions_controller(self, request):
        if self.action in ["list", "retrieve"]:
            return True
        return request.user.is_superuser

    def validate_destroy(self, instance):
        if instance.is_system:
            raise ValidationError("Cannot delete system roles")
        return super().validate_destroy(instance)

    def _add_permissions(self, instance):
        permissions = PermissionModel.objects.filter(slug__in=instance.permissions)
        RolePermission.objects.filter(role=instance).delete()
        role_permissions = []
        for permission in permissions:
            role_permissions.append(
                RolePermission(role=instance, permission=permission)
            )
        RolePermission.objects.bulk_create(role_permissions)

    def perform_create(self, instance):
        with transaction.atomic():
            super().perform_create(instance)
            if instance.permissions is not None:
                self._add_permissions(instance)

    def perform_update(self, instance):
        with transaction.atomic():
            super().perform_update(instance)
            if instance.permissions is not None:
                RolePermission.objects.filter(role=instance).delete()
                self._add_permissions(instance)

    def perform_destroy(self, instance):
        with transaction.atomic():
            super().perform_destroy(instance)
            RolePermission.objects.filter(role=instance).delete()
