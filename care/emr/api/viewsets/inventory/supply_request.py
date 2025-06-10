from django_filters import rest_framework as filters

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.supply_request import SupplyRequest
from care.emr.resources.inventory.supply_request.spec import (
    SupplyRequestReadSpec,
    SupplyRequestWriteSpec,
)
from care.utils.filters.null_filter import NullFilter


class SupplyRequestFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    priority = filters.CharFilter(lookup_expr="iexact")
    deliver_from = filters.UUIDFilter(field_name="deliver_from__external_id")
    deliver_to = filters.UUIDFilter(field_name="deliver_to__external_id")
    item = filters.UUIDFilter(field_name="item__external_id")
    deliver_from_isnull = NullFilter(field_name="deliver_from")


class SupplyRequestViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    database_model = SupplyRequest
    pydantic_model = SupplyRequestWriteSpec
    pydantic_read_model = SupplyRequestReadSpec
    filterset_class = SupplyRequestFilters
    filter_backends = [filters.DjangoFilterBackend]
