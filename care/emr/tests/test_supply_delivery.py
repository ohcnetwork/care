from django.urls import reverse
from model_bakery import baker

from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryConditionOptions,
    SupplyDeliveryTypeOptions,
)
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions
from care.utils.tests.base import CareAPITestBase


class TestSupplyDeliveryViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.patient = self.create_patient(name="Test Patient")
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.facility_location = self.create_facility_location(facility=self.facility)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            current_location=self.facility_location,
        )
        self.another_facility = self.create_facility()
        self.product = self.create_product(facility=self.facility)
        self.inventory_item = self.create_inventory_item(
            product=self.product, net_content=100, location=self.facility_location
        )
        self.delivery_order = self.create_delivery_order(
            origin=self.another_facility,
            destination=self.facility_location,
            supplier=None,
        )
        self.supply_request = self.create_supply_request(
            item=self.product,
            status="requested",
            quantity=50,
            supplied_item_condition=SupplyDeliveryConditionOptions.normal.value,
            order=None,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_read_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
            ]
        )
        self.base_url = reverse("supply_delivery-list")

    def get_detail_url(self, external_id):
        return reverse(
            "supply_delivery-detail",
            kwargs={
                "external_id": external_id,
            },
        )

    def create_product(self, **kwargs):
        from care.emr.models import ChargeItemDefinition, Product, ProductKnowledge

        product_knowledge = baker.make(ProductKnowledge)
        charge_item_definition = baker.make(ChargeItemDefinition)
        return baker.make(
            Product,
            product_knowledge=product_knowledge,
            charge_item_definition=charge_item_definition,
            **kwargs,
        )

    def create_inventory_item(self, **kwargs):
        from care.emr.models import InventoryItem

        return baker.make(InventoryItem, **kwargs)

    def create_delivery_order(self, **kwargs):
        from care.emr.models import DeliveryOrder

        return baker.make(DeliveryOrder, **kwargs)

    def create_supply_request(self, **kwargs):
        from care.emr.models import SupplyRequest

        return baker.make(SupplyRequest, **kwargs)

    def create_supply_delivery_data(
        self,
        quantity=None,
        condition=None,
        delivery_type=None,
        supplied_item=None,
        supply_request=None,
        order=None,
    ):
        return {
            "supplied_item_quantity": quantity or 50,
            "supplied_item": supplied_item or self.product.external_id,
            "supplied_item_condition": condition
            or SupplyDeliveryConditionOptions.normal.value,
            "delivery_type": delivery_type or SupplyDeliveryTypeOptions.product.value,
            "supply_request": supply_request or self.supply_request.external_id,
            "order": order or self.delivery_order.external_id,
            "supplied_inventory_item": self.inventory_item.external_id,
        }
