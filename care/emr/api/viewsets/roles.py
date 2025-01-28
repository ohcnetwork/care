# TODO Move to Security APIs

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet
from care.emr.resources.role.spec import RoleSpec
from care.security.models import RoleModel


class RoleViewSet(EMRModelReadOnlyViewSet):
    database_model = RoleModel
    pydantic_model = RoleSpec
