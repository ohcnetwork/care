from decimal import Decimal

from django.urls import reverse
from model_bakery import baker

from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
from care.emr.models.medication_dispense import DispenseOrder, MedicationDispense
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
        self.dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=self.location,
            facility=self.facility,
            status=MedicationDispenseStatus.cancelled.value,
            alternate_identifier="test-alternate-id",
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

        self.medication_request = self.create_medication_request(
            encounter=self.encounter,
            requested_product=self.product_knowledge,
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

    def create_medication_request(self, **kwargs):
        from care.emr.models import MedicationRequest

        return baker.make(MedicationRequest, **kwargs)

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

    def get_detail_url(self, external_id):
        return reverse(
            "medication-dispense-detail", kwargs={"external_id": external_id}
        )

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

    def create_medication_dispense(self, **overrides):
        defaults = {
            "status": MedicationDispenseStatus.in_progress.value,
            "encounter": self.encounter,
            "patient": self.patient,
            "location": self.location,
            "quantity": 10,
            "item": self.inventory_item,
        }
        defaults.update(overrides)
        return baker.make(MedicationDispense, **defaults)

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

    def test_create_medication_dispense_with_both_dispense_order_and_create_dispense_order(
        self,
    ):
        """
        Test creating a medication dispense with both dispense order and create dispense order
        """
        self.client.force_authenticate(user=self.superuser)

        data = self.generate_medication_dispense_data(
            order=str(self.dispense_order.external_id),
            create_dispense_order={
                "status": MedicationDispenseStatus.in_progress.value,
                "alternate_identifier": "test-alternate-id",
                "name": "Test Dispense Order",
                "note": "Test Note",
            },
        )
        response = self.client.post(self.generate_base_url(), data, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Value error, Cannot have both dispense order and create_dispense_order",
        )

    def test_create_medication_dispense_with_create_dispense_order_for_inactive_prescription(
        self,
    ):
        """Test creating a medication dispense with create dispense order for an inactive prescription"""
        self.client.force_authenticate(user=self.superuser)

        data = self.generate_medication_dispense_data(
            create_dispense_order={
                "status": MedicationDispenseStatus.in_progress.value,
                "alternate_identifier": "test-alternate-id",
                "name": "Test Dispense Order",
                "note": "Test Note",
            }
        )
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Prescription is not active",
        )

    # Testcases for update dispenses

    def test_update_medication_dispense_as_superuser(self):
        """
        Test updating a medication dispense as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        data = {
            "status": MedicationDispenseStatus.completed.value,
            "fully_dispensed": True,
        }
        response = self.client.put(
            self.get_detail_url(medication_dispense.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.completed.value
        )

    def test_update_medication_dispense_as_user_with_permission(self):
        """
        Test updating a medication dispense as a regular user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        data = {
            "status": MedicationDispenseStatus.completed.value,
            "fully_dispensed": True,
        }
        response = self.client.put(
            self.get_detail_url(medication_dispense.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.completed.value
        )

    def test_update_medication_dispense_as_user_without_permission(self):
        """
        Test updating a medication dispense as a regular user without permissions
        """
        self.client.force_authenticate(user=self.user)
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        data = {
            "status": MedicationDispenseStatus.completed.value,
            "fully_dispensed": True,
        }
        response = self.client.put(
            self.get_detail_url(medication_dispense.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to write medication dispenses",
        )

    def test_update_medication_with_authorizing_request_based_on_fully_dispensed_value(
        self,
    ):
        """
        Test updating a medication dispense with authorizing request with fully dispensed value as true which will update the medication request dispense status to completed
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(
            order=self.dispense_order,
            authorizing_request=self.medication_request,
        )
        data = {
            "status": MedicationDispenseStatus.completed.value,
            "fully_dispensed": True,
        }
        response = self.client.put(
            self.get_detail_url(medication_dispense.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.completed.value
        )
        self.assertEqual(
            response.data["authorizing_request"]["id"],
            str(self.medication_request.external_id),
        )
        self.assertEqual(
            response.data["authorizing_request"]["dispense_status"], "complete"
        )

    def test_update_medication_with_authorizing_request_based_on_fully_dispensed_value_as_false(
        self,
    ):
        """
        Test updating a medication dispense with authorizing request with fully dispensed value as false which will update the medication request dispense status to in_progress
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(
            order=self.dispense_order,
            authorizing_request=self.medication_request,
        )
        data = {
            "status": MedicationDispenseStatus.completed.value,
            "fully_dispensed": False,
        }
        response = self.client.put(
            self.get_detail_url(medication_dispense.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.completed.value
        )
        self.assertEqual(
            response.data["authorizing_request"]["id"],
            str(self.medication_request.external_id),
        )
        self.assertEqual(
            response.data["authorizing_request"]["dispense_status"], "partial"
        )

    def test_update_a_cancelled_medication_dispense(self):
        """
        Test updating a cancelled medication dispense
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(
            order=self.dispense_order,
            authorizing_request=self.medication_request,
            status=MedicationDispenseStatus.cancelled.value,
        )
        data = {
            "status": MedicationDispenseStatus.completed.value,
            "fully_dispensed": True,
        }
        response = self.client.put(
            self.get_detail_url(medication_dispense.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "No updates allowed on cancelled medication dispense",
        )

    # Testcases for listing testcases

    def test_list_medication_dispense_as_superuser(self):
        """
        Test listing medication dispenses as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(
            self.generate_base_url(), {"location": self.location.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(medication_dispense.external_id),
        )

    def test_list_medication_dispense_as_user_with_permission(self):
        """
        Test listing medication dispenses as a regular user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(
            self.generate_base_url(), {"location": self.location.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(medication_dispense.external_id),
        )

    def test_list_medication_dispense_as_user_without_permission(self):
        """
        Test listing medication dispenses as a regular user without permissions
        """
        self.client.force_authenticate(user=self.user)
        self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(
            self.generate_base_url(), {"location": self.location.external_id}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read medication dispenses",
        )

    def test_list_medication_dispense_with_encounter_filter(self):
        """
        Test listing medication dispenses with encounter filter
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(
            self.generate_base_url(), {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(medication_dispense.external_id),
        )

    def test_list_medication_dispense_without_list_filter(self):
        """
        Test listing medication dispenses without list filter should return 400
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(self.generate_base_url())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Location or encounter is required",
        )
