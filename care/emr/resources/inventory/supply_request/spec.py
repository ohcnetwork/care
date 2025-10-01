from enum import Enum

from pydantic import UUID4

from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.supply_request import RequestOrder, SupplyRequest
from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeReadSpec
from care.utils.shortcuts import get_object_or_404


class SupplyRequestStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"
    processed = "processed"
    completed = "completed"
    entered_in_error = "entered_in_error"


class BaseSupplyRequestSpec(EMRResource):
    """Base model for supply request"""

    __model__ = SupplyRequest
    __exclude__ = ["item"]

    id: UUID4 | None = None

    status: SupplyRequestStatusOptions

    quantity: float


class SupplyRequestWriteSpec(BaseSupplyRequestSpec):
    """Supply request write specification"""

    item: UUID4
    order: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.item = get_object_or_404(
            ProductKnowledge.objects.only("id").filter(external_id=self.item)
        )

        obj.order = get_object_or_404(
            RequestOrder.objects.only("id").filter(external_id=self.order)
        )
        return obj


class SupplyRequestUpdateSpec(BaseSupplyRequestSpec):
    order: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.order = get_object_or_404(
            RequestOrder.objects.only("id").filter(external_id=self.order)
        )
        return obj


class SupplyRequestReadSpec(BaseSupplyRequestSpec):
    """Supply request read specification"""

    quantity: int
    item: UUID4

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["item"] = ProductKnowledgeReadSpec.serialize(obj.item).to_json()
