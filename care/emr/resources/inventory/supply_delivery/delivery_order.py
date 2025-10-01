from enum import Enum

from pydantic import UUID4

from care.emr.models.location import FacilityLocation
from care.emr.models.organization import Organization
from care.emr.models.supply_delivery import DeliveryOrder
from care.emr.resources.base import EMRResource
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.organization.spec import (
    OrganizationReadSpec,
    OrganizationTypeChoices,
)
from care.emr.tagging.base import SingleFacilityTagManager
from care.utils.shortcuts import get_object_or_404


class SupplyDeliveryOrderStatusOptions(str, Enum):
    draft = "draft"
    pending = "pending"
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


class SupplyDeliveryOrderWriteSpec(BaseSupplyDeliveryOrderSpec):
    supplier: UUID4 | None = None
    origin: UUID4 | None = None
    destination: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.destination = get_object_or_404(
            FacilityLocation.objects.only("id").filter(external_id=self.destination)
        )
        if self.origin:
            obj.origin = get_object_or_404(
                FacilityLocation.objects.only("id").filter(external_id=self.origin)
            )

        if self.supplier:
            obj.supplier = get_object_or_404(
                Organization.objects.only("id").filter(
                    external_id=self.supplier,
                    org_type=OrganizationTypeChoices.product_supplier.value,
                )
            )

        return obj


class SupplyDeliveryOrderReadSpec(BaseSupplyDeliveryOrderSpec):
    origin: dict | None = None
    destination: dict
    supplier: dict | None = None
    tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.origin:
            mapping["origin"] = FacilityLocationListSpec.serialize(obj.origin).to_json()
        mapping["destination"] = FacilityLocationListSpec.serialize(
            obj.destination
        ).to_json()
        if obj.supplier:
            mapping["supplier"] = OrganizationReadSpec.serialize(obj.supplier).to_json()
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)
