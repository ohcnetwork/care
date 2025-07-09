from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.decorators import action
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
from care.emr.models.supply_delivery import SupplyDelivery
from care.emr.resources.inventory.inventory_item.create_inventory_item import (
    create_inventory_item,
)
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    BaseSupplyDeliverySpec,
    SupplyDeliveryReadSpec,
    SupplyDeliveryRetrieveSpec,
    SupplyDeliveryStatusOptions,
    SupplyDeliveryWriteSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.null_filter import NullFilter


class SupplyDeliveryFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    origin = filters.UUIDFilter(field_name="origin__external_id")
    destination = filters.UUIDFilter(field_name="destination__external_id")
    supplied_item = filters.UUIDFilter(field_name="supplied_item__external_id")
    supplied_item_product_knowledge = filters.UUIDFilter(
        field_name="supplied_item__product_knowledge__external_id"
    )
    supplied_inventory_item_product_knowledge = filters.UUIDFilter(
        field_name="supplied_inventory_item__product__product_knowledge__external_id"
    )
    supply_request = filters.UUIDFilter(field_name="supply_request__external_id")
    origin_isnull = NullFilter(field_name="origin")
    supplier = filters.UUIDFilter(field_name="supplier__external_id")


class SupplyDeliveryViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRUpsertMixin,
    EMRBaseViewSet,
):
    database_model = SupplyDelivery
    pydantic_model = SupplyDeliveryWriteSpec
    pydantic_update_model = BaseSupplyDeliverySpec
    pydantic_read_model = SupplyDeliveryReadSpec
    pydantic_retrieve_model = SupplyDeliveryRetrieveSpec
    filterset_class = SupplyDeliveryFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def perform_create(self, instance):
        instance.status = SupplyDeliveryStatusOptions.in_progress.value
        return super().perform_create(instance)

    def get_update_pydantic_model(self):
        if self.action == "update_as_receiver":
            return BaseSupplyDeliverySpec  # Same for now
        return super().get_update_pydantic_model()

    @action(detail=True, methods=["PUT"])
    def update_as_receiver(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def perform_update(self, instance):
        with transaction.atomic():
            old_instance = self.database_model.objects.get(id=instance.id)
            if instance.status != old_instance.status:
                if old_instance.status == SupplyDeliveryStatusOptions.completed.value:
                    raise ValidationError("Supply delivery already completed")
                if (
                    instance.status == SupplyDeliveryStatusOptions.completed.value
                    and not instance.origin
                ):
                    # Handle Product Inventory and resync
                    instance.supplied_inventory_item = create_inventory_item(
                        instance.supplied_item, instance.destination
                    )
            super().perform_update(instance)
            if instance.supplied_inventory_item:
                sync_inventory_item(instance.supplied_inventory_item)
            return instance

    def authorize_location_read(self, location):
        if not AuthorizationController.call(
            "can_list_facility_supply_delivery", self.request.user, location
        ):
            raise PermissionDenied("Cannot list supply deliveries")

    def authorize_location_write(self, location_obj):
        if not AuthorizationController.call(
            "can_write_facility_supply_delivery", self.request.user, location_obj
        ):
            raise PermissionDenied("Cannot write supply deliveries")

    def authorize_update(self, request_obj, model_instance):
        if self.action == "update_as_receiver":
            self.authorize_location_write(model_instance.deliver_from)
        else:
            self.authorize_location_write(model_instance.deliver_to)

    def authorize_create(self, instance):
        origin = get_object_or_404(FacilityLocation, external_id=instance.origin)
        self.authorize_location_write(origin)

    def authorize_retrieve(self, model_instance):
        allowed = AuthorizationController.call(
            "can_list_facility_supply_delivery",
            self.request.user,
            model_instance.destination,
        )
        if model_instance.origin:
            allowed = allowed or AuthorizationController.call(
                "can_list_facility_supply_delivery",
                self.request.user,
                model_instance.origin,
            )
        if not allowed:
            raise PermissionDenied("Cannot read supply deliveries")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            allowed = False
            if "origin" in self.request.GET:
                from_location = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["deliver_from"]
                )
                self.authorize_location_read(from_location)
                queryset = queryset.filter(origin=from_location)
                allowed = True
            if "destination" in self.request.GET:
                to_location = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["deliver_to"]
                )
                self.authorize_location_read(to_location)
                queryset = queryset.filter(destination=to_location)
                allowed = True
            if not allowed:
                raise PermissionDenied("Either origin or destination is required")
        return queryset
