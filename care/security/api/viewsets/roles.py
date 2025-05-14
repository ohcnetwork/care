from django.db import transaction
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.resources.role.spec import (
    PermissionManageSpec,
    RoleConfig,
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
        if self.action in [
            "create",
            "update",
            "destroy",
            "update_permissions",
            "bulk_create_roles",
        ]:
            return request.user.is_superuser
        return False

    def validate_destroy(self, instance):
        if instance.is_system:
            raise ValidationError("Cannot delete system roles")
        return super().validate_destroy(instance)

    def validate_data(self, instance, model_obj=None):
        if model_obj and model_obj.is_system:
            raise ValidationError("Cannot update system roles")

        if instance.is_system:
            raise ValidationError("Cannot create system roles")

        name_changed = not model_obj or instance.name != model_obj.name
        if name_changed and RoleModel.objects.filter(name=instance.name).exists():
            raise ValidationError("Role with this name already exists")

    @extend_schema(request=PermissionManageSpec)
    @action(methods=["POST"], detail=True)
    def update_permissions(self, request, *args, **kwargs):
        request_data = PermissionManageSpec(**request.data)

        role = self.get_object()
        if role.is_system:
            return Response(
                data={"error": "Cannot add permissions to system roles"}, status=400
            )

        permissions = PermissionModel.objects.filter(slug__in=request_data.permissions)

        with transaction.atomic():
            RolePermission.objects.filter(role=role).delete()

            role_permissions = []
            for permission in permissions:
                role_permissions.append(
                    RolePermission(role=role, permission=permission)
                )

            RolePermission.objects.bulk_create(role_permissions)

        return Response(
            data={"message": "Permissions updated successfully"}, status=200
        )

    class BulkPermissionManageSpec(BaseModel):
        roles: list[RoleConfig]

    @extend_schema(request=BulkPermissionManageSpec)
    @action(methods=["POST"], detail=False)
    def bulk_create_roles(self, request, *args, **kwargs):
        request_data = self.BulkPermissionManageSpec(**request.data)
        role_configs = request_data.roles

        with transaction.atomic():
            for role_config in role_configs:
                role_data = role_config.role
                permission_slugs = role_config.permissions

                role_obj = RoleModel.objects.filter(name=role_data.name).first()

                if role_obj:
                    if role_obj.is_system:
                        continue
                    RolePermission.objects.filter(role=role_obj).delete()
                else:
                    role_obj = RoleModel.objects.create(
                        name=role_data.name,
                        description=role_data.description,
                        is_system=False,
                        temp_deleted=False,
                    )

                valid_permissions = PermissionModel.objects.filter(
                    slug__in=permission_slugs
                )
                role_permissions = [
                    RolePermission(role=role_obj, permission=perm)
                    for perm in valid_permissions
                ]
                RolePermission.objects.bulk_create(role_permissions)

        return Response(
            data={"message": "Roles and permissions processed successfully"}, status=200
        )
