from collections import defaultdict
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from care.emr.locks.billing import lock_inventory_items
from care.emr.models.supply_delivery import SupplyDelivery
from care.emr.resources.inventory.inventory_item.create_inventory_item import (
    create_inventory_item,
)
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)


def cancel_supply_deliveries(delivery_order, status, user):
    """Cancel remaining children and resync stock while the caller holds the order lock."""
    deliveries = list(
        SupplyDelivery.objects.filter(order=delivery_order)
        .exclude(
            status__in=[
                SupplyDeliveryStatusOptions.abandoned.value,
                SupplyDeliveryStatusOptions.entered_in_error.value,
            ]
        )
        .select_related("supplied_inventory_item__product")
    )
    inventory_items = {}
    stock_to_remove = defaultdict(Decimal)
    for delivery in deliveries:
        source = delivery.supplied_inventory_item
        destination = create_inventory_item(source.product, delivery_order.destination)
        inventory_items[destination.pk] = destination
        quantity = delivery.supplied_item_quantity or 0
        if delivery.status == SupplyDeliveryStatusOptions.completed.value:
            stock_to_remove[destination.pk] += quantity
        if delivery_order.origin_id:
            inventory_items[source.pk] = source
            if delivery.status in [
                SupplyDeliveryStatusOptions.in_progress.value,
                SupplyDeliveryStatusOptions.completed.value,
            ]:
                stock_to_remove[source.pk] -= quantity

    with lock_inventory_items(inventory_items.values()):
        # A source can also be the destination, so validate the net withdrawal.
        for item_id, quantity in stock_to_remove.items():
            if quantity > 0 and inventory_items[item_id].net_content < quantity:
                raise ValidationError("Inventory item does not have enough stock")
        for delivery in deliveries:
            delivery.status = status
            delivery.updated_by = user
            delivery.save(update_fields=["status", "updated_by", "modified_date"])
        for inventory_item in inventory_items.values():
            sync_inventory_item(inventory_item=inventory_item)
