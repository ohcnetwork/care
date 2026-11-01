"""
Inventory Item needs to be synced to track the current availability
The current availability can change based on the dispense and delivery in the system
"""

from django.db.models import Sum

from care.emr.locks.billing import InventoryItemLock
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.models.supply_delivery import SupplyDelivery
from care.emr.resources.inventory.inventory_item.create_inventory_item import (
    create_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)
from care.emr.resources.medication.dispense.spec import (
    MEDICATION_DISPENSE_CANCELLED_STATUSES,
)


def sync_inventory_item(location=None, product=None, inventory_item=None):
    """
    Sync the inventory item to track the current availability
    Current availability
    = Delivery Requests completed at location with inventory item
    - Delivery Requests in progress from this location
    - Dispense Requests created from this location
    """
    if inventory_item:
        product = inventory_item.product
        location = inventory_item.location
    current_location = location
    if not inventory_item:
        inventory_item = create_inventory_item(product, location)

    with InventoryItemLock(inventory_item):
        delivery_requests_incoming = SupplyDelivery.objects.filter(
            order__destination=current_location,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item__product=product,
        )
        delivery_requests_incoming_quantity = (
            delivery_requests_incoming.aggregate(
                total_quantity=Sum("supplied_item_quantity")
            ).get("total_quantity")
            or 0
        )
        delivery_requests_in_progress_completed = SupplyDelivery.objects.filter(
            order__origin__isnull=False,
            supplied_inventory_item=inventory_item,
            status__in=[
                SupplyDeliveryStatusOptions.in_progress.value,
                SupplyDeliveryStatusOptions.completed.value,
            ],
        )
        delivery_requests_in_progress_completed_quantity = (
            delivery_requests_in_progress_completed.aggregate(
                total_quantity=Sum("supplied_item_quantity")
            ).get("total_quantity")
            or 0
        )
        dispenses = (
            MedicationDispense.objects.filter(item=inventory_item)
            .exclude(status__in=MEDICATION_DISPENSE_CANCELLED_STATUSES)
            .aggregate(total_quantity=Sum("quantity"))
        ).get("total_quantity") or 0

        total_quantity = (
            delivery_requests_incoming_quantity
            - delivery_requests_in_progress_completed_quantity
            - dispenses
        )

        inventory_item.net_content = total_quantity
        inventory_item.save(update_fields=["net_content", "modified_date"])
