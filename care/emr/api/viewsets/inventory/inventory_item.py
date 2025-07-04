from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.location import FacilityLocation
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
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_location_obj(self):
        return get_object_or_404(
            FacilityLocation, external_id=self.kwargs["location_external_id"]
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        location = self.get_location_obj()
        return queryset.filter(location=location)
