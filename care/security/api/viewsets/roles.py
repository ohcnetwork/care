from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, model_validator
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.resources.role.spec import RoleCreateSpec, RoleReadSpec
from care.security.models import PermissionModel, RoleModel, RolePermission
from care.security.permissions.base import PermissionController


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
            "add_permissions",
            "remove_permissions",
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

    class PermissionManageSpec(BaseModel):
        permissions: list[str]

        @model_validator(mode="after")
        def validate_permissions(self):
            valid_permissions = PermissionController.get_permissions().keys()
            for permission in self.permissions:
                if permission not in valid_permissions:
                    error = f"Invalid permission slug: {permission}."
                    raise ValidationError(error)

    @extend_schema(request=PermissionManageSpec)
    @action(methods=["POST"], detail=True)
    def add_permissions(self, request, *args, **kwargs):
        request_data = self.PermissionManageSpec(**request.data)

        role = self.get_object()

        if role.is_system:
            return Response(
                data={"error": "Cannot add permissions to system roles"}, status=400
            )

        permissions = request_data.permissions

        existing_permissions_on_role = RolePermission.objects.filter(
            role=role
        ).values_list("permission__slug", flat=True)

        new_permissions_slugs = set(permissions) - set(existing_permissions_on_role)

        new_permissions = PermissionModel.objects.filter(slug__in=new_permissions_slugs)
        role_permissions = []
        for permission in new_permissions:
            role_permissions.append(RolePermission(role=role, permission=permission))

        RolePermission.objects.bulk_create(role_permissions)

        return Response(data={"message": "Permissions added successfully"}, status=200)

    @extend_schema(request=PermissionManageSpec)
    @action(methods=["POST"], detail=True)
    def remove_permissions(self, request, *args, **kwargs):
        request_data = self.PermissionManageSpec(**request.data)

        role = self.get_object()

        if role.is_system:
            return Response(
                data={"error": "Cannot remove permissions from system roles"},
                status=400,
            )

        permissions = request_data.permissions

        RolePermission.objects.filter(
            role=role, permission__slug__in=permissions
        ).delete()

        return Response(
            data={"message": "Permissions removed successfully"}, status=200
        )
