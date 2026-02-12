from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
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
from care.emr.models.medication_dispense import DispenseOrder, MedicationDispense
from care.emr.resources.charge_item.handle_charge_item_cancel import (
    handle_charge_item_cancel,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.medication.dispense.dispense_order import (
    BaseMedicationDispenseOrderSpec,
    MedicationDispenseOrderReadSpec,
    MedicationDispenseOrderRetrieveSpec,
    MedicationDispenseOrderStatusOptions,
    MedicationDispenseOrderWriteSpec,
)
from care.emr.resources.medication.request.spec import MedicationRequestDispenseStatus
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter, DummyUUIDFilter
from care.utils.filters.multiselect import MultiSelectFilter


def cancel_dispense_order(instance):
    related_dispenses = MedicationDispense.objects.filter(order=instance)
    for dispense in related_dispenses:
        if dispense.charge_item:
            handle_charge_item_cancel(instance.charge_item)
        dispense.charge_item.status = ChargeItemStatusOptions.aborted.value
        dispense.authorizing_request.dispense_status = (
            MedicationRequestDispenseStatus.incomplete.value
        )
        dispense.authorizing_request.save(update_fields=["dispense_status"])
        dispense.authorizing_request = None
        dispense.charge_item.save()
        dispense.save()


class DispenseOrderFilters(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    location = DummyUUIDFilter()
    include_children = DummyBooleanFilter()
    created_by = filters.UUIDFilter(field_name="created_by__external_id")


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
    pydantic_retrieve_model = MedicationDispenseOrderRetrieveSpec
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

    def perform_update(self, instance):
        # TODO : Add a Lock to ensure that the dispense order is not updated concurrently
        with transaction.atomic():
            old_object = DispenseOrder.objects.get(id=instance.id)
            if old_object.status != instance.status:
                if old_object.status in [
                    MedicationDispenseOrderStatusOptions.abandoned.value,
                    MedicationDispenseOrderStatusOptions.entered_in_error.value,
                ]:
                    raise ValidationError(
                        "Dispense order already abandoned or entered in error"
                    )
                if (
                    old_object.status
                    == MedicationDispenseOrderStatusOptions.completed.value
                ):
                    if instance.status not in [
                        MedicationDispenseOrderStatusOptions.abandoned.value,
                        MedicationDispenseOrderStatusOptions.entered_in_error.value,
                    ]:
                        raise ValidationError("Dispense order can only be cancelled")
                    cancel_dispense_order(instance)
            return super().perform_update(instance)

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        return super().perform_create(instance)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        if self.authorize_pharmacist(facility):
            return
        location = get_object_or_404(FacilityLocation, external_id=instance.location)
        if not location.facility == facility:
            raise ValidationError("Location must be in the same facility")
        if self.authorize_location_write(location):
            return
        raise PermissionDenied("You do not have permission to create dispense order")

    def authorize_update(self, request_obj, model_instance):
        if self.authorize_pharmacist(model_instance.facility):
            return
        if self.authorize_location_write(model_instance.location):
            return
        raise PermissionDenied("You do not have permission to update dispense order")

    def authorize_retrieve(self, model_instance):
        facility = self.get_facility_obj()
        if self.authorize_pharmacist(facility):
            return
        if self.authorize_location_read(model_instance.location):
            return
        raise PermissionDenied("You do not have permission to read dispense order")

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
                if not self.authorize_location_read(location):
                    raise PermissionDenied(
                        "You do not have permission to read dispense order"
                    )
                include_children = (
                    self.request.GET.get("include_children", "false").lower() == "true"
                )
                if include_children:
                    queryset = queryset.filter(
                        Q(location=location)
                        | Q(location__parent_cache__overlap=[location.id])
                    )
                else:
                    queryset = queryset.filter(location=location)
            else:
                raise ValidationError("Location is required for non-pharmacists")
        return queryset
