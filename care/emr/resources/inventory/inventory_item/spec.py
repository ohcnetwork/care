from enum import Enum

from pydantic import UUID4

from care.emr.models.inventory_item import InventoryItem
from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.product.spec import ProductReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec


class InventoryItemStatusOptions(str, Enum):
    active = "active"
    inactive = "inactive"
    entered_in_error = "entered_in_error"


class BaseInventoryItemSpec(EMRResource):
    """Base model for inventory item"""

    __model__ = InventoryItem
    __exclude__ = []

    id: UUID4 | None = None

    status: InventoryItemStatusOptions


class InventoryItemWriteSpec(BaseInventoryItemSpec):
    """Inventory item write specification"""


class InventoryItemReadSpec(BaseInventoryItemSpec):
    """Supply delivery read specification"""

    net_content: float
    product: float
    location: dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["product"] = ProductReadSpec.serialize(obj.product).to_json()
        mapping["location"] = FacilityLocationListSpec.serialize(obj.location).to_json()


class InventoryItemRetrieveSpec(InventoryItemReadSpec):
    pass
