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
from care.emr.models.medication_dispense import DispenseOrder
from care.emr.resources.medication.dispense.dispense_order import (
    BaseMedicationDispenseOrderSpec,
    MedicationDispenseOrderReadSpec,
    MedicationDispenseOrderWriteSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyUUIDFilter


class DispenseOrderFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    created_date = filters.DateRangeFilter()
    patient = filters.UUIDFilter(field_name="patient__external_id")
    location = DummyUUIDFilter()


class DispenseOrderViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    database_model = DispenseOrder
    pydantic_model = MedicationDispenseOrderWriteSpec
    pydantic_update_model = BaseMedicationDispenseOrderSpec
    pydantic_read_model = MedicationDispenseOrderReadSpec
    filterset_class = DispenseOrderFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def authorize_location_read(self, location):
        return AuthorizationController.call(
            "can_list_facility_supply_delivery", self.request.user, location
        )

    def authorize_location_write(self, location_obj):
        return AuthorizationController.call(
            "can_write_facility_supply_delivery", self.request.user, location_obj
        )

    def authorize_pharmacist(self, facility):
        return AuthorizationController.call(
            "can_view_as_pharmacist", self.request.user, facility
        )

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        if instance.location.facility != instance.facility:
            raise PermissionDenied("Location must be in the same facility")
        return super().perform_create(instance)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        if self.authorize_pharmacist(facility):
            return
        if self.authorize_location_write(
            get_object_or_404(
                FacilityLocation, external_id=instance.location, facility=facility
            )
        ):
            return
        raise PermissionDenied("You do not have permission to create dispense order")

    def authorize_update(self, request_obj, model_instance):
        if self.authorize_pharmacist(model_instance.facility):
            return
        if self.authorize_location_write(model_instance.location):
            return
        raise PermissionDenied("You do not have permission to create dispense order")

    def authorize_retrieve(self, model_instance):
        facility = self.get_facility_obj()
        if self.authorize_pharmacist(facility):
            return
        if self.authorize_location_read(model_instance.location):
            return
        raise PermissionDenied("You do not have permission to create dispense order")

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = super().get_queryset().filter(facility=facility)
        if self.action == "list":
            if self.authorize_pharmacist(facility):
                queryset = queryset.filter(facility=facility)
            elif "location" in self.request.GET:
                location = get_object_or_404(
                    FacilityLocation,
                    external_id=self.request.GET["location"],
                    facility=facility,
                )
                self.authorize_location_read(location)
                queryset = queryset.filter(location=location)
            else:
                raise PermissionDenied("Location is required for non-pharmacists")
        return queryset
