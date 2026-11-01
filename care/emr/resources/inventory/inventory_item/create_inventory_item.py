from care.emr.locks.billing import InventoryCreationLock
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.location import FacilityLocation
from care.emr.models.product import Product
from care.emr.resources.inventory.inventory_item.spec import InventoryItemStatusOptions


def create_inventory_item(product: Product, location: FacilityLocation):
    inventory_obj = (
        InventoryItem.objects.filter(product=product, location=location)
        .only("id")
        .first()
    )
    if inventory_obj:
        return inventory_obj
    with InventoryCreationLock(product):
        inventory_obj, _ = InventoryItem.objects.get_or_create(
            product=product,
            location=location,
            defaults={
                "status": InventoryItemStatusOptions.active.value,
                "net_content": 0,
            },
        )
    return inventory_obj
