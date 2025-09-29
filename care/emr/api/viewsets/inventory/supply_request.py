from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.location import FacilityLocation
from care.emr.models.supply_request import RequestOrder, SupplyRequest
from care.emr.resources.inventory.supply_request.spec import (
    SupplyRequestReadSpec,
    SupplyRequestUpdateSpec,
    SupplyRequestWriteSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter, DummyUUIDFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404


class SupplyRequestFilters(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    origin = DummyUUIDFilter()
    destination = DummyUUIDFilter()
    item = filters.UUIDFilter(field_name="item__external_id")
    supplier = filters.UUIDFilter(field_name="order__supplier__external_id")
    include_children = DummyBooleanFilter()
    order = DummyUUIDFilter()


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
    pydantic_update_model = SupplyRequestUpdateSpec
    pydantic_read_model = SupplyRequestReadSpec
    filterset_class = SupplyRequestFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def authorize_location_read(self, location_obj, raise_error=True):
        if not AuthorizationController.call(
            "can_list_facility_supply_request", self.request.user, location_obj
        ):
            if raise_error:
                raise PermissionDenied("Cannot list supply requests")
            return False
        return True

    def authorize_location_write(self, location_obj, raise_error=True):
        if not AuthorizationController.call(
            "can_write_facility_supply_request", self.request.user, location_obj
        ):
            if raise_error:
                raise PermissionDenied("Cannot write supply requests")
            return False
        return True

    def authorize_create(self, instance):
        order = get_object_or_404(RequestOrder, external_id=instance.order)
        self.authorize_order_write(order)

    def authorize_update(self, request_obj, model_instance):
        self.authorize_order_write(model_instance.order)

    def authorize_retrieve(self, model_instance):
        self.authorize_order_read(model_instance.order)

    def authorize_order_read(self, order):
        allowed = False
        if order.origin:
            allowed = allowed or self.authorize_location_read(
                order.origin, raise_error=False
            )
        allowed = allowed or self.authorize_location_read(
            order.destination, raise_error=False
        )
        if not allowed:
            raise PermissionDenied("Cannot read supply requests")

    def authorize_order_write(self, order):
        allowed = False
        if order.origin:
            allowed = allowed or self.authorize_location_write(
                order.origin, raise_error=False
            )
        allowed = allowed or self.authorize_location_write(
            order.destination, raise_error=False
        )
        if not allowed:
            raise PermissionDenied("Cannot write supply requests")

    def filter_location_queryset(
        self, queryset, attribute, location_obj, include_children=False
    ):
        if include_children:
            queryset = queryset.filter(
                Q(**{attribute: location_obj})
                | Q(**{attribute + "__parent_cache__overlap": [location_obj.id]})
            )
        else:
            queryset = queryset.filter(**{attribute: location_obj})
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            include_children = (
                self.request.GET.get("include_children", "false").lower() == "true"
            )
            filtered = False
            if "order" in self.request.GET:
                order = get_object_or_404(
                    RequestOrder, external_id=self.request.GET["order"]
                )
                self.authorize_order_read(order)
                queryset = queryset.filter(order=order)
                filtered = True
            if "destination" in self.request.GET:
                destination = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["destination"]
                )
                self.authorize_location_read(destination)
                queryset = self.filter_location_queryset(
                    queryset, "order__destination", destination, include_children
                )
                filtered = True
            if "origin" in self.request.GET:
                origin = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["origin"]
                )
                self.authorize_location_read(origin)
                queryset = self.filter_location_queryset(
                    queryset, "order__origin", origin, include_children
                )
                filtered = True
            if not filtered:
                raise ValidationError("No filters provided")
        return queryset
