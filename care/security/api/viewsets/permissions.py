from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet
from care.emr.resources.role.spec import PermissionSpec
from care.security.models import PermissionModel


class PermissionViewSet(EMRModelReadOnlyViewSet):
    database_model = PermissionModel
    pydantic_model = PermissionSpec

    lookup_field = "slug"
