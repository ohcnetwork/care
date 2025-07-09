import datetime
from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4, model_validator

from care.emr.models.inventory_item import InventoryItem
from care.emr.models.location import FacilityLocation
from care.emr.models.organization import Organization
from care.emr.models.product import Product
from care.emr.models.supply_delivery import SupplyDelivery
from care.emr.models.supply_request import SupplyRequest
from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.inventory_item.spec import InventoryItemReadSpec
from care.emr.resources.inventory.product.spec import ProductReadSpec
from care.emr.resources.inventory.supply_request.spec import SupplyRequestReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.organization.spec import (
    OrganizationReadSpec,
    OrganizationTypeChoices,
)
from care.emr.resources.user.spec import UserSpec


class SupplyDeliveryStatusOptions(str, Enum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"
    entered_in_error = "entered_in_error"


SUPPLY_DELIVERY_CANCELLED_STATUSES = [
    SupplyDeliveryStatusOptions.abandoned.value,
    SupplyDeliveryStatusOptions.entered_in_error.value,
]


class SupplyDeliveryTypeOptions(str, Enum):
    product = "product"
    device = "device"


class SupplyDeliveryConditionOptions(str, Enum):
    normal = "normal"
    damaged = "damaged"


class BaseSupplyDeliverySpec(EMRResource):
    """Base model for supply delivery"""

    __model__ = SupplyDelivery
    __exclude__ = [
        "supplied_item",
        "origin",
        "destination",
        "supply_request",
        "supplied_inventory_item",
        "supplier",
    ]

    id: UUID4 | None = None

    status: SupplyDeliveryStatusOptions
    supplied_item_condition: SupplyDeliveryConditionOptions | None = None


class SupplyDeliveryWriteSpec(BaseSupplyDeliverySpec):
    """Supply delivery write specification"""

    supplied_item_quantity: float
    supplied_item: UUID4 | None = None
    supplied_inventory_item: UUID4 | None = None
    supplier: UUID4 | None = None
    origin: UUID4 | None = None
    destination: UUID4
    supply_request: UUID4 | None = None

    @model_validator(mode="after")
    def validate_supplied_item(self):
        """
        When the delivery is taken from outside a facility,
        there is no inventory item yet.
        When the delivery is inside a facility, inventory item is moved.
        This allows parents to move child's stock and maintain them.
        """
        if self.origin and not self.supplied_inventory_item:
            raise ValueError(
                "supplied_inventory_item is required when origin is provided"
            )
        if not self.origin and not self.supplied_item:
            raise ValueError("supplied_item is required when origin is not provided")
        if self.supplied_item and self.supplied_inventory_item:
            raise ValueError(
                "supplied_item and supplied_inventory_item cannot both be provided"
            )
        return self

    def perform_extra_deserialization(self, is_update, obj):
        obj.destination = get_object_or_404(
            FacilityLocation.objects.only("id").filter(external_id=self.destination)
        )

        if self.supplied_item:
            obj.supplied_item = get_object_or_404(
                Product.objects.only("id").filter(
                    external_id=self.supplied_item, facility=obj.destination.facility
                )
            )
        if self.supplied_inventory_item:
            obj.supplied_inventory_item = get_object_or_404(
                InventoryItem.objects.only("id").filter(
                    external_id=self.supplied_inventory_item,
                    location__facility=obj.destination.facility,
                )
            )

        if self.origin:
            obj.origin = get_object_or_404(
                FacilityLocation.objects.only("id").filter(external_id=self.origin)
            )
        if self.supply_request:
            obj.supply_request = get_object_or_404(
                SupplyRequest.objects.only("id").filter(external_id=self.supply_request)
            )
        if self.supplier:
            obj.supplier = get_object_or_404(
                Organization.objects.only("id").filter(
                    external_id=self.supplier,
                    org_type=OrganizationTypeChoices.product_supplier.value,
                )
            )
        return obj


class SupplyDeliveryReadSpec(BaseSupplyDeliverySpec):
    """Supply delivery read specification"""

    supplied_item_quantity: int
    supplied_item: dict | None = None
    origin: dict | None = None
    destination: dict
    created_date: datetime.datetime
    modified_date: datetime.datetime
    supplied_inventory_item: dict | None = None
    supplier: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.origin:
            mapping["origin"] = FacilityLocationListSpec.serialize(obj.origin).to_json()
        mapping["destination"] = FacilityLocationListSpec.serialize(
            obj.destination
        ).to_json()
        if obj.supplied_item:
            mapping["supplied_item"] = ProductReadSpec.serialize(
                obj.supplied_item
            ).to_json()
        if obj.supplied_inventory_item:
            mapping["supplied_inventory_item"] = InventoryItemReadSpec.serialize(
                obj.supplied_inventory_item
            ).to_json()
        if obj.supplier:
            mapping["supplier"] = OrganizationReadSpec.serialize(obj.supplier).to_json()


class SupplyDeliveryRetrieveSpec(SupplyDeliveryReadSpec):
    """Supply delivery retrieve specification"""

    supply_request: dict | None = None
    created_by: UserSpec = dict
    updated_by: UserSpec = dict

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        if obj.supply_request:
            mapping["supply_request"] = SupplyRequestReadSpec.serialize(
                obj.supply_request
            ).to_json()
        cls.serialize_audit_users(mapping, obj)
