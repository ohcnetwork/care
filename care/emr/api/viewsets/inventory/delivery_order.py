from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.location import FacilityLocation
from care.emr.models.supply_delivery import DeliveryOrder
from care.emr.resources.inventory.supply_delivery.delivery_order import (
    BaseSupplyDeliveryOrderSpec,
    SupplyDeliveryOrderReadSpec,
    SupplyDeliveryOrderWriteSpec,
)
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter, DummyUUIDFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.filters.null_filter import NullFilter


class DeliveryOrderFilters(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    created_date = filters.DateRangeFilter()
    supplier = filters.UUIDFilter(field_name="supplier__external_id")

    origin = DummyUUIDFilter()
    destination = DummyUUIDFilter()
    include_children = DummyBooleanFilter()
    origin_isnull = NullFilter(field_name="origin")


class DeliveryOrderViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRTagMixin,
    EMRBaseViewSet,
):
    database_model = DeliveryOrder
    pydantic_model = SupplyDeliveryOrderWriteSpec
    pydantic_update_model = BaseSupplyDeliveryOrderSpec
    pydantic_read_model = SupplyDeliveryOrderReadSpec
    filterset_class = DeliveryOrderFilters
    filter_backends = [
        filters.DjangoFilterBackend,
        OrderingFilter,
        SingleFacilityTagFilter,
    ]
    ordering_fields = ["created_date", "modified_date"]
    resource_type = TagResource.supply_delivery_order

    def get_facility_from_instance(self, instance):
        return instance.destination.facility  # Overide as needed

    def authorize_location_read(self, location_obj, raise_error=True):
        if not AuthorizationController.call(
            "can_list_facility_supply_delivery", self.request.user, location_obj
        ):
            if raise_error:
                raise PermissionDenied("Cannot list supply requests")
            return False
        return True

    def authorize_location_write(self, location_obj, raise_error=True):
        if not AuthorizationController.call(
            "can_write_facility_supply_delivery", self.request.user, location_obj
        ):
            if raise_error:
                raise PermissionDenied("Cannot write supply requests")
            return False
        return True

    def perform_create(self, instance):
        if (
            instance.origin
            and instance.origin.facility != instance.destination.facility
        ):
            raise PermissionDenied(
                "Origin and destination must be in the same facility"
            )
        return super().perform_create(instance)

    def authorize_create(self, instance):
        """
        If the order is an external order, then destination is the owner,
        else the owner is the origin.
        """
        if instance.origin:
            origin_location = get_object_or_404(
                FacilityLocation, external_id=instance.origin
            )
            self.authorize_location_write(origin_location)
        else:
            destination_location = get_object_or_404(
                FacilityLocation, external_id=instance.destination
            )
            self.authorize_location_write(destination_location)

    def authorize_update(self, request_obj, model_instance):
        """
        If the order is an external order, then destination is the owner,
        else the owner is the origin.
        """
        # TODO: Order Destination permission to be figured out
        if model_instance.origin:
            self.authorize_location_write(model_instance.origin)
        else:
            self.authorize_location_write(model_instance.destination)

    def authorize_retrieve(self, model_instance):
        allowed = False
        if model_instance.origin:
            allowed = allowed or self.authorize_location_read(model_instance.origin)
        allowed = allowed or self.authorize_location_read(model_instance.destination)
        if not allowed:
            raise PermissionDenied("Cannot read delivery orders")

    def get_location_obj(self, external_id):
        return get_object_or_404(FacilityLocation, external_id=external_id)

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
            if "origin" in self.request.GET:
                origin = self.get_location_obj(self.request.GET["origin"])
                self.authorize_location_read(origin)
                queryset = self.filter_location_queryset(
                    queryset, "origin", origin, include_children
                )
            if "destination" in self.request.GET:
                destination = self.get_location_obj(self.request.GET["destination"])
                self.authorize_location_read(destination)
                queryset = self.filter_location_queryset(
                    queryset, "destination", destination, include_children
                )
        return queryset
