from enum import Enum

from pydantic import UUID4

from care.emr.models.supply_request import RequestOrder
from care.emr.resources.base import EMRResource


class SupplyRequestOrderStatusOptions(str, Enum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"
    entered_in_error = "entered_in_error"


SUPPLY_REQUEST_ORDER_COMPLETED_STATUSES = [
    SupplyRequestOrderStatusOptions.abandoned.value,
    SupplyRequestOrderStatusOptions.entered_in_error.value,
    SupplyRequestOrderStatusOptions.completed.value,
]


class BaseSupplyRequestOrderSpec(EMRResource):
    __model__ = RequestOrder

    id: UUID4 | None = None

    status: SupplyRequestOrderStatusOptions
    name: str
    note: str | None = None


class SupplyRequestOrderReadSpec(BaseSupplyRequestOrderSpec):
    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
