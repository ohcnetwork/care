from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
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
