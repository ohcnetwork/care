from django_filters import rest_framework as filters

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet
from care.emr.resources.role.spec import PermissionSpec
from care.security.models import PermissionModel


class PermissionFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class PermissionViewSet(EMRModelReadOnlyViewSet):
    database_model = PermissionModel
    pydantic_model = PermissionSpec
    filterset_class = PermissionFilter
    filter_backends = [filters.DjangoFilterBackend]
    lookup_field = "slug"
