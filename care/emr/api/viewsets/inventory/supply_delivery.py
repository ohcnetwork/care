from django.db import transaction
from django.db.models import Q
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
from care.emr.models.inventory_item import InventoryItem
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
from care.utils.filters.dummy_filter import DummyBooleanFilter, DummyUUIDFilter
from care.utils.filters.null_filter import NullFilter
from care.utils.shortcuts import get_object_or_404


class SupplyDeliveryFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    origin = DummyUUIDFilter()
    destination = DummyUUIDFilter()
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
    include_children = DummyBooleanFilter()


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

    def validate_data(self, instance, model_obj=None):
        if not model_obj and instance.origin:
            # TODO : Check if origin is part of the facility
            # TODO : Check if the supplied inventory item is part of the origin or its children
            origin = get_object_or_404(FacilityLocation, external_id=instance.origin)
            if instance.supplied_inventory_item:
                inventory_item = get_object_or_404(
                    InventoryItem, external_id=instance.supplied_inventory_item
                )
                self.validate_stock(
                    origin, inventory_item.product, instance.supplied_item_quantity
                )

        return super().validate_data(instance, model_obj)

    def validate_stock(self, location, product, quantity):
        inventory_item = InventoryItem.objects.filter(
            location=location, product=product
        ).first()
        if not inventory_item or inventory_item.net_content < quantity:
            raise ValidationError("Insufficient stock")

    def perform_create(self, instance):
        if instance.origin:
            # When the delivery is from outside facility,
            # all statuses are allowed to be updated by the recieving location
            instance.status = SupplyDeliveryStatusOptions.in_progress.value
        if instance.supplied_item:
            instance.supplied_inventory_item = create_inventory_item(
                instance.supplied_item, instance.destination
            )
        super().perform_create(instance)
        self.sync_inventory_item(instance)

    def get_update_pydantic_model(self):
        if self.action == "update_as_receiver":
            return BaseSupplyDeliverySpec  # Same for now
        return super().get_update_pydantic_model()

    @action(detail=True, methods=["PUT"])
    def update_as_receiver(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def sync_inventory_item(self, instance):
        if instance.supplied_inventory_item:
            sync_inventory_item(
                instance.destination, instance.supplied_inventory_item.product
            )
            if instance.origin:
                sync_inventory_item(
                    instance.origin, instance.supplied_inventory_item.product
                )

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
            self.sync_inventory_item(instance)
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
        if not model_instance.origin:
            self.authorize_location_write(model_instance.destination)
            return
        if self.action == "update_as_receiver":
            self.authorize_location_write(model_instance.destination)
        else:
            self.authorize_location_write(model_instance.origin)

    def authorize_create(self, instance):
        if instance.origin:
            origin = get_object_or_404(FacilityLocation, external_id=instance.origin)
            self.authorize_location_write(origin)
        else:
            destination = get_object_or_404(
                FacilityLocation, external_id=instance.destination
            )
            self.authorize_location_write(destination)
            # TODO : Check if the user has permission to recieve outside stock

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
            include_children = (
                self.request.GET.get("include_children", "false").lower() == "true"
            )
            if "origin" in self.request.GET:
                from_location = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["origin"]
                )
                self.authorize_location_read(from_location)
                if include_children:
                    queryset = queryset.filter(
                        Q(origin=from_location)
                        | Q(origin__parent_cache__overlap=[from_location.id])
                    )
                else:
                    queryset = queryset.filter(origin=from_location)
                allowed = True
            if "destination" in self.request.GET:
                to_location = get_object_or_404(
                    FacilityLocation, external_id=self.request.GET["destination"]
                )
                self.authorize_location_read(to_location)
                if include_children:
                    queryset = queryset.filter(
                        Q(destination=to_location)
                        | Q(destination__parent_cache__overlap=[to_location.id])
                    )
                else:
                    queryset = queryset.filter(destination=to_location)
                allowed = True
            if not allowed:
                raise PermissionDenied("Either origin or destination is required")
        return queryset
