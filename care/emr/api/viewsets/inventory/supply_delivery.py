from django.db import transaction
from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

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
from care.emr.models.supply_delivery import DeliveryOrder, SupplyDelivery
from care.emr.models.supply_request import RequestOrder
from care.emr.resources.inventory.inventory_item.create_inventory_item import (
    create_inventory_item,
)
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.delivery_order import (
    SupplyDeliveryOrderReadSpec,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryReadSpec,
    SupplyDeliveryRetrieveSpec,
    SupplyDeliveryStatusOptions,
    SupplyDeliveryUpdateSpec,
    SupplyDeliveryWriteSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter, DummyUUIDFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.filters.null_filter import NullFilter
from care.utils.shortcuts import get_object_or_404


class SupplyDeliveryFilters(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
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
    origin_isnull = NullFilter(field_name="order__origin")
    supplier = filters.UUIDFilter(field_name="order__supplier__external_id")
    include_children = DummyBooleanFilter()
    order = DummyUUIDFilter()
    request_order = DummyUUIDFilter()


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
    pydantic_update_model = SupplyDeliveryUpdateSpec
    pydantic_read_model = SupplyDeliveryReadSpec
    pydantic_retrieve_model = SupplyDeliveryRetrieveSpec
    filterset_class = SupplyDeliveryFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def validate_data(self, instance, model_obj=None):
        if not model_obj:
            order = get_object_or_404(DeliveryOrder, external_id=instance.order)
            if order.origin and instance.supplied_inventory_item:
                inventory_item = get_object_or_404(
                    InventoryItem,
                    external_id=instance.supplied_inventory_item,
                )
                parents = inventory_item.location.parent_cache
                if not (
                    order.origin.id in parents
                    or order.origin.id == inventory_item.location.id
                ):
                    raise ValidationError(
                        "Supplied inventory item is not part of the origin or its children"
                    )
                if inventory_item.net_content < instance.supplied_item_quantity:
                    raise ValidationError("Insufficient stock")

        return super().validate_data(instance, model_obj)

    def perform_create(self, instance):
        if instance.order.origin:
            # When the delivery is from outside facility,
            # all statuses are allowed to be updated by the recieving location
            instance.status = SupplyDeliveryStatusOptions.in_progress.value
        if instance.supplied_item:
            instance.supplied_inventory_item = create_inventory_item(
                instance.supplied_item, instance.order.destination
            )
        super().perform_create(instance)
        self.sync_inventory_item(instance)

    def sync_inventory_item(self, instance):
        if instance.supplied_inventory_item:
            sync_inventory_item(
                location=instance.order.destination,
                product=instance.supplied_inventory_item.product,
            )
            if instance.order.origin:
                sync_inventory_item(inventory_item=instance.supplied_inventory_item)

    def perform_update(self, instance):
        with transaction.atomic():
            old_instance = self.database_model.objects.get(id=instance.id)
            if instance.status != old_instance.status:
                if old_instance.status == SupplyDeliveryStatusOptions.completed.value:
                    raise ValidationError("Supply delivery already completed")
                if (
                    instance.status == SupplyDeliveryStatusOptions.completed.value
                    and not instance.order.origin
                ):
                    # Handle Product Inventory and resync
                    instance.supplied_inventory_item = create_inventory_item(
                        instance.supplied_item, instance.order.destination
                    )
            super().perform_update(instance)
            self.sync_inventory_item(instance)
        return instance

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

    def authorize_update(self, request_obj, model_instance):
        self.authorize_order_write(model_instance.order)

    def authorize_create(self, instance):
        order = get_object_or_404(DeliveryOrder, external_id=instance.order)
        self.authorize_order_write(order)

    def authorize_retrieve(self, model_instance):
        self.authorize_order_read(model_instance.order)

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

    @action(detail=False, methods=["GET"])
    def delivery_orders(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if "request_order" not in request.GET:
            raise ValidationError("request_order is required")
        orders = queryset.values("order_id").distinct()[:100]
        orders_qs = DeliveryOrder.objects.filter(id__in=orders)
        response = [
            SupplyDeliveryOrderReadSpec.serialize(order).to_json()
            for order in orders_qs
        ]
        return Response({"results": response})

    def get_queryset(self):
        queryset = self.database_model.objects.all()
        if self.action == "list":
            queryset = queryset.order_by("-id")
        if self.action in ["list", "delivery_orders"]:
            include_children = (
                self.request.GET.get("include_children", "false").lower() == "true"
            )
            filtered = False
            if "order" in self.request.GET:
                order = get_object_or_404(
                    DeliveryOrder, external_id=self.request.GET["order"]
                )
                self.authorize_order_read(order)
                queryset = queryset.filter(order=order)
                filtered = True
            if "request_order" in self.request.GET:
                order = get_object_or_404(
                    RequestOrder, external_id=self.request.GET["request_order"]
                )
                self.authorize_order_read(order)
                # TODO Optimize without joins
                queryset = queryset.filter(supply_request__order=order)
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
