from pydantic import UUID4, BaseModel, ValidationError, model_validator

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
    name: str
    description: str
    is_system: bool | None = False


class RoleCreateSpec(RoleBaseSpec):
    def perform_extra_deserialization(self, is_update, obj):
        if is_update:
            self.is_system = obj.is_system
        else:
            self.is_system = False


class RoleReadSpec(RoleBaseSpec):
    permissions: list[PermissionSpec]

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["permissions"] = obj.get_permissions_for_role()
        return mapping


class PermissionManageSpec(BaseModel):
    permissions: list[str]

    @model_validator(mode="after")
    def validate_permissions(self):
        valid_permissions = PermissionController.get_permissions().keys()
        self.permissions = list(set(self.permissions))  # Remove duplicates
        for permission in self.permissions:
            if permission not in valid_permissions:
                error = f"Invalid permission slug: {permission}."
                raise ValidationError(error)
        return self


class RoleConfig(PermissionManageSpec):
    role: RoleCreateSpec

    @model_validator(mode="after")
    def validate_role_and_permissions(self):
        system_roles = RoleModel.objects.filter(is_system=True).values_list(
            "name", flat=True
        )
        role = self.role.name
        if role in system_roles:
            error = f"Role {role} already exists."
            raise ValidationError(error)
        return self
