from pydantic import UUID4

from care.emr.resources.base import EMRResource
from care.security.models import PermissionModel, RoleModel


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
    is_system: bool


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
