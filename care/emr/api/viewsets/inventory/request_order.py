from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
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
from care.emr.resources.inventory.supply_request.request_order import (
    BaseSupplyRequestOrderSpec,
    SupplyRequestOrderReadSpec,
)
from care.security.authorization.base import AuthorizationController


class RequestOrderFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    date = filters.DateFilter(field_name="created_date")


class RequestOrderViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    database_model = RequestOrder
    pydantic_model = BaseSupplyRequestOrderSpec
    pydantic_read_model = SupplyRequestOrderReadSpec
    filterset_class = RequestOrderFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_location_obj(self):
        return get_object_or_404(
            FacilityLocation, external_id=self.kwargs["location_external_id"]
        )

    def authorize_location_read(self, location_obj):
        if not AuthorizationController.call(
            "can_list_facility_supply_request", self.request.user, location_obj
        ):
            raise PermissionDenied("Cannot list supply requests")

    def authorize_location_write(self, location_obj):
        if not AuthorizationController.call(
            "can_write_facility_supply_request", self.request.user, location_obj
        ):
            raise PermissionDenied("Cannot write supply requests")

    def perform_create(self, instance):
        instance.location = self.get_location_obj()
        return super().perform_create(instance)

    def authorize_create(self, instance):
        self.authorize_location_write(self.get_location_obj())

    def authorize_update(self, request_obj, model_instance):
        self.authorize_location_write(model_instance.location)

    def authorize_retrieve(self, model_instance):
        if "destination" in self.request.GET:
            # Retrieve access is present if the
            # order is referenced in another location
            from_location = get_object_or_404(
                FacilityLocation, external_id=self.request.GET["destination"]
            )
            if not SupplyRequest.objects.filter(
                order=model_instance, deliver_to=from_location
            ).exists():
                raise PermissionDenied("This Order is not referenced in this location")
            location = from_location
        else:
            location = model_instance.location

        self.authorize_location_read(location)

    def get_queryset(self):
        queryset = super().get_queryset()
        location = self.get_location_obj()
        if self.action == "list":
            self.authorize_location_read(location)
        return queryset.filter(location=location)
