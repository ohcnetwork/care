from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.decorators import action
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
from care.emr.models.supply_request import SupplyRequest
from care.emr.resources.inventory.supply_request.spec import (
    SupplyRequestReadSpec,
    SupplyRequestUpdateSpec,
    SupplyRequestWriteSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.null_filter import NullFilter


class SupplyRequestFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    priority = filters.CharFilter(lookup_expr="iexact")
    item = filters.UUIDFilter(field_name="item__external_id")
    deliver_from_isnull = NullFilter(field_name="deliver_from")
    supplier = filters.UUIDFilter(field_name="supplier__external_id")


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

    def authorize_create(self, instance):
        to_location = get_object_or_404(
            FacilityLocation, external_id=instance.deliver_to
        )
        self.authorize_location_write(to_location)

    def authorize_update(self, request_obj, model_instance):
        if self.action == "update_as_fulfiller":
            self.authorize_location_write(model_instance.deliver_from)
        else:
            self.authorize_location_write(model_instance.deliver_to)

    def authorize_retrieve(self, model_instance):
        allowed = AuthorizationController.call(
            "can_list_facility_supply_request",
            self.request.user,
            model_instance.deliver_to,
        )
        if model_instance.deliver_from:
            allowed = allowed or AuthorizationController.call(
                "can_list_facility_supply_request",
                self.request.user,
                model_instance.deliver_from,
            )
        if not allowed:
            raise PermissionDenied("Cannot read supply requests")

    def get_update_pydantic_model(self):
        if self.action == "update_as_receiver":
            return SupplyRequestUpdateSpec  # Same for now
        return super().get_update_pydantic_model()

    @action(detail=True, methods=["PUT"])
    def update_as_receiver(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            allowed = False
            if "deliver_from" in self.request.GET:
                from_location = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["deliver_from"]
                )
                self.authorize_location_read(from_location)
                queryset = queryset.filter(deliver_from=from_location)
                allowed = True
            if "deliver_to" in self.request.GET:
                to_location = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["deliver_to"]
                )
                self.authorize_location_read(to_location)
                queryset = queryset.filter(deliver_to=to_location)
                allowed = True
            # Check permission in root to view all incomplete requests
            if "facility" in self.request.GET:
                facility = get_object_or_404(
                    Facility, external_id=self.request.GET["facility"]
                )
                if not AuthorizationController.call(
                    "can_list_all_facility_supply_request", self.request.user, facility
                ):
                    raise PermissionDenied("Cannot list supply requests")
                queryset = queryset.filter(deliver_to__facility=facility)
                allowed = True
            if not allowed:
                raise PermissionDenied("Either deliver_from or deliver_to is required")
        return queryset
