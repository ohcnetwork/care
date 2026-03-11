from decimal import Decimal

from django.urls import reverse
from model_bakery import baker

from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
from care.emr.models.medication_dispense import DispenseOrder
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)
from care.emr.resources.medication.dispense.spec import MedicationDispenseStatus
from care.security.permissions.medication import MedicationPermissions
from care.utils.tests.base import CareAPITestBase


class MedicationDispenseAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user(username="superuser")
        self.user = self.create_user(username="testuser")
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.superuser, name="Test Facility")
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Org"
        )
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            status_history={"history": []},
            encounter_class_history={"history": []},
        )
        self.supplier = self.create_organization(name="Test Supplier")
        self.location = self.create_facility_location(
            self.facility,
            name="Pharmacy",
            facility_organization=self.facility_organization,
        )

        self.role = self.create_role_with_permissions(
            permissions=[
                MedicationPermissions.read_medication_dispense.name,
                MedicationPermissions.write_medication_dispense.name,
            ]
        )

        self.product_knowledge = baker.make(
            "emr.ProductKnowledge",
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-test-product",
            name="Test Product",
            status="active",
            product_type="medication",
            code={"code": "test", "display": "Test", "system": "http://test"},
        )

        self.product = baker.make(
            "emr.Product",
            facility=self.facility,
            product_knowledge=self.product_knowledge,
            status="active",
            product_type="medication",
        )

        self.inventory_item = self.create_inventory_item(
            location=self.location,
            product=self.product,
            status="active",
            net_content=50,
        )
        self.delivery_order_destination_external = self.create_delivery_order(
            destination=self.location,
            supplier=self.supplier,
        )
        self.purchase_order_destination = self.create_supply_delivery(
            order=self.delivery_order_destination_external,
            supplied_item_quantity=Decimal(50),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item,
        )

    def create_facility_location(self, facility, facility_organization, **kwargs):
        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    def create_dispense_order(self, **kwargs):
        return baker.make(DispenseOrder, **kwargs)

    def create_inventory_item(self, **kwargs):
        from care.emr.models import InventoryItem

        return baker.make(InventoryItem, **kwargs)

    def create_delivery_order(self, **kwargs):
        from care.emr.models import DeliveryOrder

        return baker.make(DeliveryOrder, **kwargs)

    def generate_base_url(self):
        return reverse("medication-dispense-list")

    def create_supply_delivery(self, **kwargs):
        from care.emr.models import SupplyDelivery

        supply_delivery = baker.make(SupplyDelivery, **kwargs)
        if supply_delivery.order.origin:
            sync_inventory_item(inventory_item=supply_delivery.supplied_inventory_item)
        else:
            sync_inventory_item(
                location=supply_delivery.order.destination,
                product=supply_delivery.supplied_inventory_item.product,
            )
        return supply_delivery

    def get_detail_url(self):
        return reverse("medication-dispense-detail")

    def generate_medication_dispense_data(self, **overrides):
        data = {
            "status": MedicationDispenseStatus.in_progress.value,
            "encounter": str(self.encounter.external_id),
            "patient": str(self.patient.external_id),
            "location": str(self.location.external_id),
            "quantity": 10,
            "item": str(self.inventory_item.external_id),
        }
        data.update(overrides)
        return data

    def test_create_medication_dispense_as_superuser(self):
        """
        Test creating a medication dispense as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_medication_dispense_data()
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.in_progress.value
        )
        self.assertEqual(response.data["quantity"], "10")
        self.assertEqual(
            response.data["item"]["id"], str(self.inventory_item.external_id)
        )
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.net_content, 40)

    def test_create_medication_dispense_as_user_with_permission(self):
        """
        Test creating a medication dispense as a regular user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        data = self.generate_medication_dispense_data()
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.in_progress.value
        )
        self.assertEqual(response.data["quantity"], "10")
        self.assertEqual(
            response.data["item"]["id"], str(self.inventory_item.external_id)
        )
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.net_content, 40)

    def test_create_medication_dispense_as_user_without_permission(self):
        """
        Test creating a medication dispense as a regular user without permissions
        """
        self.client.force_authenticate(user=self.user)
        data = self.generate_medication_dispense_data()
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to write medication dispenses",
        )

    def test_create_medication_dispense_with_more_quantity_than_stock(self):
        """
        Test creating a medication dispense with quantity more than available in inventory
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_medication_dispense_data(quantity=60)
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Inventory item does not have enough stock",
        )
