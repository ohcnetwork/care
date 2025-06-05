from django_filters import rest_framework as filters

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.models.inventory_item import InventoryItem
from care.emr.resources.inventory.inventory_item.spec import (
    InventoryItemReadSpec,
    InventoryItemRetrieveSpec,
    InventoryItemWriteSpec,
)


class InventoryItemFilters(filters.FilterSet):
    product_knowledge = filters.UUIDFilter(
        field_name="product__product_knowledge__external_id"
    )
    status = filters.CharFilter(lookup_expr="iexact")
    net_content_gt = filters.NumberFilter(field_name="net_content", lookup_expr="gt")
    net_content = filters.RangeFilter(field_name="net_content")


class InventoryItemViewSet(EMRRetrieveMixin, EMRListMixin, EMRBaseViewSet):
    database_model = InventoryItem
    pydantic_model = InventoryItemWriteSpec
    pydantic_read_model = InventoryItemReadSpec
    pydantic_retrieve_model = InventoryItemRetrieveSpec
    filterset_class = InventoryItemFilters
    filter_backends = [filters.DjangoFilterBackend]
