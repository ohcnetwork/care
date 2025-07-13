from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.location import FacilityLocation
from care.emr.resources.inventory.inventory_item.spec import (
    InventoryItemReadSpec,
    InventoryItemRetrieveSpec,
    InventoryItemWriteSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter


class InventoryItemFilters(filters.FilterSet):
    product_knowledge = filters.UUIDFilter(
        field_name="product__product_knowledge__external_id"
    )
    status = filters.CharFilter(lookup_expr="iexact")
    net_content_gt = filters.NumberFilter(field_name="net_content", lookup_expr="gt")
    include_children = DummyBooleanFilter()


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

    def authorize_location_read(self, location):
        if not AuthorizationController.call(
            "can_list_location_inventory_item", self.request.user, location
        ):
            raise PermissionDenied("You do not have permission to read inventory items")

    def authorize_retrieve(self, model_instance):
        self.authorize_location_read(model_instance.location)

    def get_queryset(self):
        queryset = super().get_queryset()
        location = self.get_location_obj()
        self.authorize_location_read(location)
        include_children = (
            self.request.GET.get("include_children", "false").lower() == "true"
        )
        if include_children:
            queryset = queryset.filter(
                Q(location__parent_cache__overlap=[location.id]) | Q(location=location)
            )
        else:
            queryset = queryset.filter(location=location)
        return queryset
