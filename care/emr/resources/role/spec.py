from pydantic import UUID4, model_validator
from pydantic_core.core_schema import ValidationInfo

from care.emr.resources.base import EMRResource
from care.security.models import PermissionModel, RoleModel
from care.security.permissions.base import PermissionController


class PermissionSpec(EMRResource):
    __model__ = PermissionModel
    name: str
    description: str
    slug: str
    context: str


class RoleBaseSpec(EMRResource):
    __model__ = RoleModel
    __exclude__ = ["permissions"]

    id: UUID4 | None = None
    name: str | None = None
    description: str | None = None
    is_system: bool | None = False


class RoleCreateSpec(RoleBaseSpec):
    permissions: list[PermissionController.get_enum()] | None = []

    @model_validator(mode="after")
    def validate_role(self, info: ValidationInfo):
        context = info.context or {}
        is_update = context.get("is_update", False)
        model_obj = context.get("object")

        if not is_update and (not self.name or not self.name.strip()):
            raise ValueError("Role name cannot be empty")

        qs = RoleModel.objects.filter(name__iexact=self.name)
        if is_update and model_obj:
            qs = qs.exclude(id=model_obj.id)

        if qs.exists():
            raise ValueError("Role with this name already exists")

        if model_obj and model_obj.is_system:
            raise ValueError("Cannot update system roles")
        if self.is_system:
            raise ValueError("Cannot create system roles")

        if self.permissions:
            self.permissions = list(set(self.permissions))

        return self

    def perform_extra_deserialization(self, is_update, obj):
        if self.permissions:
            obj.permissions = self.permissions
        else:
            obj.permissions = None


class RoleReadSpec(RoleBaseSpec):
    permissions: list[PermissionSpec]

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["permissions"] = obj.get_permissions_for_role()
        return mapping
