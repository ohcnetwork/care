from enum import Enum

from pydantic import UUID4

from care.emr.models.supply_delivery import DeliveryOrder
from care.emr.resources.base import EMRResource


class SupplyDeliveryOrderStatusOptions(str, Enum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"
    entered_in_error = "entered_in_error"


SUPPLY_DELIVERY_ORDER_COMPLETED_STATUSES = [
    SupplyDeliveryOrderStatusOptions.abandoned.value,
    SupplyDeliveryOrderStatusOptions.entered_in_error.value,
    SupplyDeliveryOrderStatusOptions.completed.value,
]


class BaseSupplyDeliveryOrderSpec(EMRResource):
    __model__ = DeliveryOrder

    id: UUID4 | None = None

    status: SupplyDeliveryOrderStatusOptions
    name: str
    note: str | None = None


class SupplyDeliveryOrderReadSpec(BaseSupplyDeliveryOrderSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
