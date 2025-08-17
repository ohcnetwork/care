from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4

from care.emr.models.location import FacilityLocation
from care.emr.models.organization import Organization
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.supply_request import SupplyRequest
from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.organization.spec import (
    OrganizationReadSpec,
    OrganizationTypeChoices,
)


class SupplyRequestStatusOptions(str, Enum):
    draft = "draft"
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"
    processed = "processed"
    completed = "completed"
    entered_in_error = "entered_in_error"


class SupplyRequestIntentOptions(str, Enum):
    proposal = "proposal"
    plan = "plan"
    directive = "directive"
    order = "order"
    original_order = "original_order"
    reflex_order = "reflex_order"
    filler_order = "filler_order"
    instance_order = "instance_order"


class SupplyRequestCategoryOptions(str, Enum):
    central = "central"
    nonstock = "nonstock"


class SupplyRequestPriorityOptions(str, Enum):
    routine = "routine"
    urgent = "urgent"
    asap = "asap"
    stat = "stat"


class SupplyRequestReason(str, Enum):
    patient_care = "patient_care"
    ward_stock = "ward_stock"


class BaseSupplyRequestSpec(EMRResource):
    """Base model for supply request"""

    __model__ = SupplyRequest
    __exclude__ = ["item", "deliver_to", "deliver_from", "supplier"]

    id: UUID4 | None = None

    status: SupplyRequestStatusOptions
    intent: SupplyRequestIntentOptions
    category: SupplyRequestCategoryOptions
    priority: SupplyRequestPriorityOptions
    reason: SupplyRequestReason
    quantity: float


class SupplyRequestWriteSpec(BaseSupplyRequestSpec):
    """Supply request write specification"""

    deliver_from: UUID4 | None = None
    deliver_to: UUID4
    item: UUID4
    supplier: UUID4 | None = None

    def perform_extra_deserialization(self, is_update, obj):
        obj.item = get_object_or_404(
            ProductKnowledge.objects.only("id").filter(external_id=self.item)
        )
        obj.deliver_to = get_object_or_404(
            FacilityLocation.objects.only("id").filter(external_id=self.deliver_to)
        )
        if self.deliver_from:
            obj.deliver_from = get_object_or_404(
                FacilityLocation.objects.only("id").filter(
                    external_id=self.deliver_from
                )
            )
        if self.supplier:
            obj.supplier = get_object_or_404(
                Organization.objects.only("id").filter(external_id=self.supplier)
            )
            if obj.supplier.org_type != OrganizationTypeChoices.product_supplier.value:
                msg = f"Supplier organization must be of type product_supplier, got: {obj.supplier.org_type}"
                raise ValueError(msg)
        return obj


class SupplyRequestUpdateSpec(BaseSupplyRequestSpec):
    pass


class SupplyRequestReadSpec(BaseSupplyRequestSpec):
    """Supply request read specification"""

    quantity: int
    item: UUID4
    deliver_from: dict
    deliver_to: dict
    supplier: OrganizationReadSpec | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.deliver_from:
            mapping["deliver_from"] = FacilityLocationListSpec.serialize(
                obj.deliver_from
            ).to_json()
        mapping["deliver_to"] = FacilityLocationListSpec.serialize(
            obj.deliver_to
        ).to_json()
        mapping["item"] = ProductKnowledgeReadSpec.serialize(obj.item).to_json()
        if obj.supplier:
            mapping["supplier"] = OrganizationReadSpec.serialize(obj.supplier).to_json()
