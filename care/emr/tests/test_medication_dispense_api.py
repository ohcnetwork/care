from decimal import Decimal

from django.urls import reverse
from model_bakery import baker

from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
from care.emr.models.medication_dispense import DispenseOrder, MedicationDispense
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionStatusOptions,
)
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)
from care.emr.resources.medication.dispense.spec import MedicationDispenseStatus
from care.emr.resources.medication.request.spec import MedicationRequestDispenseStatus
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
        self.charge_item_definition = ChargeItemDefinition.objects.create(
            facility=self.facility,
            status=ChargeItemDefinitionStatusOptions.active.value,
            title="Test Charge Definition",
            slug=f"f-{self.facility.external_id}-test-charge-def",
            price_components=[
                {
                    "monetary_component_type": "base",
                    "currency": "INR",
                    "amount": "100.00",
                }
            ],
        )

        self.product = self.create_product(
            facility=self.facility,
            product_type="medication",
            product_knowledge=self.product_knowledge,
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
            requester=self.user,
        )

    def create_facility_location(self, facility, facility_organization, **kwargs):
        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    def create_product(self, **kwargs):
        return baker.make("emr.Product", **kwargs)

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

    def generate_summary_url(self):
        return reverse("medication-dispense-summary")

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

    def test_create_medication_dispense_with_product_with_chargeitem_definition(self):
        """
        Test creating a medication dispense with a product that has a charge item definition
        """
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product(
            facility=self.facility,
            product_type="medication",
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        inventory_item = self.create_inventory_item(
            location=self.location,
            product=product,
            status="active",
            net_content=50,
        )
        data = self.generate_medication_dispense_data(
            item=str(inventory_item.external_id)
        )
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.in_progress.value
        )
        self.assertIsNotNone(response.data["charge_item"])
        self.assertEqual(
            response.data["charge_item"]["charge_item_definition"]["id"],
            str(self.charge_item_definition.external_id),
        )

    def test_create_medication_dispense_with_authorizing_request(self):
        """
        Test creating a medication dispense with an authorizing medication request
        """
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product(
            facility=self.facility,
            product_type="medication",
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        inventory_item = self.create_inventory_item(
            location=self.location,
            product=product,
            status="active",
            net_content=50,
        )
        data = self.generate_medication_dispense_data(
            item=str(inventory_item.external_id),
            authorizing_request=str(self.medication_request.external_id),
        )
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.in_progress.value
        )
        self.assertEqual(
            response.data["authorizing_request"]["id"],
            str(self.medication_request.external_id),
        )

    def test_create_medication_dispense_with_fully_dispensed_value_as_true(self):
        """
        Test creating a medication dispense with fully dispensed value as true which will update the medication request dispense status to completed
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_medication_dispense_data(
            authorizing_request=str(self.medication_request.external_id),
            fully_dispensed=True,
        )
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.in_progress.value
        )
        self.assertEqual(
            response.data["authorizing_request"]["id"],
            str(self.medication_request.external_id),
        )
        self.assertEqual(
            response.data["authorizing_request"]["dispense_status"],
            MedicationRequestDispenseStatus.complete.value,
        )

    def test_create_medication_dispense_with_fully_dispensed_value_as_false(self):
        """
        Test creating a medication dispense with fully dispensed value as false which will update the medication request dispense status to in_progress
        """
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_medication_dispense_data(
            authorizing_request=str(self.medication_request.external_id),
            fully_dispensed=False,
        )
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.in_progress.value
        )
        self.assertEqual(
            response.data["authorizing_request"]["id"],
            str(self.medication_request.external_id),
        )
        self.assertEqual(
            response.data["authorizing_request"]["dispense_status"],
            MedicationRequestDispenseStatus.partial.value,
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

    def test_cancel_medication_dispense_with_chargeitem_and_authorizing_request(self):
        """
        Test cancelling a medication dispense which has a charge item and authorizing request should update the charge item status to cancelled and medication request dispense status to cancelled
        """
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product(
            facility=self.facility,
            product_type="medication",
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        inventory_item = self.create_inventory_item(
            location=self.location,
            product=product,
            status="active",
            net_content=50,
        )
        data = self.generate_medication_dispense_data(
            item=str(inventory_item.external_id),
            authorizing_request=str(self.medication_request.external_id),
        )
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        data = {
            "status": MedicationDispenseStatus.cancelled.value,
            "fully_dispensed": True,
        }
        response = self.client.put(
            self.get_detail_url(response.data["id"]), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.cancelled.value
        )
        self.assertIsNone(response.data["authorizing_request"])
        self.assertIsNotNone(response.data["charge_item"])
        self.assertEqual(response.data["charge_item"]["status"], "aborted")

    def test_cancel_medication_dispense_without_authorizing_request(self):
        """
        Test cancelling a medication dispense which does not have an authorizing request should update the medication dispense status to cancelled without any error
        """
        self.client.force_authenticate(user=self.superuser)
        product = self.create_product(
            facility=self.facility,
            product_type="medication",
            product_knowledge=self.product_knowledge,
            charge_item_definition=self.charge_item_definition,
        )
        inventory_item = self.create_inventory_item(
            location=self.location,
            product=product,
            status="active",
            net_content=50,
        )
        data = self.generate_medication_dispense_data(
            item=str(inventory_item.external_id),
        )
        response = self.client.post(self.generate_base_url(), data, format="json")
        self.assertEqual(response.status_code, 200)
        data = {
            "status": MedicationDispenseStatus.cancelled.value,
            "fully_dispensed": True,
        }
        response = self.client.put(
            self.get_detail_url(response.data["id"]), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], MedicationDispenseStatus.cancelled.value
        )
        self.assertIsNone(response.data["authorizing_request"])
        self.assertIsNotNone(response.data["charge_item"])
        self.assertEqual(response.data["charge_item"]["status"], "aborted")

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

    def test_list_medication_dispense_without_encounter_permission(self):
        """
        Test listing medication dispenses with encounter filter without encounter read permission should return 403
        """
        self.client.force_authenticate(user=self.user)
        self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(
            self.generate_base_url(), {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read medication dispenses",
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

    def test_list_medication_dispense_with_location_include_children_filter(self):
        """
        Test listing medication dispenses with location include children filter
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_medication_dispense(order=self.dispense_order)
        child_location = self.create_facility_location(
            self.facility,
            name="Child Location",
            facility_organization=self.facility_organization,
            parent=self.location,
        )
        another_dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=child_location,
            facility=self.facility,
            status=MedicationDispenseStatus.in_progress.value,
            alternate_identifier="test-alternate-id-2",
        )
        self.create_medication_dispense(
            order=another_dispense_order, location=child_location
        )
        response = self.client.get(
            self.generate_base_url(),
            {"location": self.location.external_id, "include_children": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_medication_dispense_with_location_include_children_filter_false(self):
        """
        Test listing medication dispenses with location include children filter as false should return only medication dispenses for the specified location
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        child_location = self.create_facility_location(
            self.facility,
            name="Child Location",
            facility_organization=self.facility_organization,
            parent=self.location,
        )
        another_dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=child_location,
            facility=self.facility,
            status=MedicationDispenseStatus.in_progress.value,
            alternate_identifier="test-alternate-id-2",
        )
        self.create_medication_dispense(
            order=another_dispense_order, location=child_location
        )
        response = self.client.get(
            self.generate_base_url(),
            {"location": self.location.external_id, "include_children": False},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(medication_dispense.external_id),
        )

    #  Testcases for retrieve api

    def test_retrieve_medication_dispense_as_superuser(self):
        """
        Test retrieving a medication dispense as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(self.get_detail_url(medication_dispense.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            str(medication_dispense.external_id),
        )

    def test_retrieve_medication_dispense_as_user_with_permission(self):
        """
        Test retrieving a medication dispense as a regular user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(self.get_detail_url(medication_dispense.external_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            str(medication_dispense.external_id),
        )

    def test_retrieve_medication_dispense_as_user_without_permission(self):
        """
        Test retrieving a medication dispense as a regular user without permissions
        """
        self.client.force_authenticate(user=self.user)
        medication_dispense = self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(self.get_detail_url(medication_dispense.external_id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read medication dispense",
        )

    # Testcases for summary api

    def test_summary_medication_dispense_as_superuser(self):
        """
        Test summary of medication dispenses as a superuser
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_medication_dispense(order=self.dispense_order)
        another_dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=self.location,
            facility=self.facility,
            status=MedicationDispenseStatus.in_progress.value,
            alternate_identifier="test-alternate-id-2",
        )
        self.create_medication_dispense(order=another_dispense_order)
        response = self.client.get(
            self.generate_summary_url(), {"location": self.location.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["count"], 2)

    def test_summary_medication_dispense_as_user_with_permission(self):
        """
        Test summary of medication dispenses as a regular user with permissions
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.create_medication_dispense(order=self.dispense_order)
        another_dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=self.location,
            facility=self.facility,
            status=MedicationDispenseStatus.in_progress.value,
            alternate_identifier="test-alternate-id-2",
        )
        self.create_medication_dispense(order=another_dispense_order)
        response = self.client.get(
            self.generate_summary_url(), {"location": self.location.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["count"], 2)

    def test_summary_medication_dispense_as_user_without_location_permission(self):
        """
        Test summary of medication dispenses as a regular user without permissions
        """
        self.client.force_authenticate(user=self.user)
        self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(
            self.generate_summary_url(), {"location": self.location.external_id}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read medication dispenses",
        )

    def test_summary_medication_dispense_without_list_filter(self):
        """
        Test summary of medication dispenses without list filter should return 400
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_medication_dispense(order=self.dispense_order)
        response = self.client.get(self.generate_summary_url())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Location or encounter is required",
        )

    def test_summary_medication_dispense_with_encounter_filter(self):
        """
        Test summary of medication dispenses with encounter filter
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_medication_dispense(order=self.dispense_order)
        another_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        another_dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=self.location,
            facility=self.facility,
            status=MedicationDispenseStatus.in_progress.value,
            alternate_identifier="test-alternate-id-2",
        )
        self.create_medication_dispense(
            order=another_dispense_order, encounter=another_encounter
        )
        response = self.client.get(
            self.generate_summary_url(), {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["count"], 1)

    def test_summary_medication_dispense_with_encounter_filter_without_encounter_permission(
        self,
    ):
        """
        Test summary of medication dispenses with encounter filter without encounter read permission should return 403
        """
        self.client.force_authenticate(user=self.user)
        self.create_medication_dispense(order=self.dispense_order)
        another_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        another_dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=self.location,
            facility=self.facility,
            status=MedicationDispenseStatus.in_progress.value,
            alternate_identifier="test-alternate-id-2",
        )
        self.create_medication_dispense(
            order=another_dispense_order, encounter=another_encounter
        )
        response = self.client.get(
            self.generate_summary_url(), {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to read medication dispenses",
        )

    def test_summary_medication_dispense_with_multiple_dispenses_for_multiple_encounters(
        self,
    ):
        """
        Test summary of medication dispenses with multiple dispenses for multiple encounters should return correct count for each encounter
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_medication_dispense(order=self.dispense_order)
        self.create_medication_dispense(order=self.dispense_order)
        another_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        child_location = self.create_facility_location(
            self.facility,
            name="Child Location",
            facility_organization=self.facility_organization,
            parent=self.location,
        )

        another_dispense_order = self.create_dispense_order(
            patient=self.patient,
            location=child_location,
            facility=self.facility,
            status=MedicationDispenseStatus.in_progress.value,
            alternate_identifier="test-alternate-id-2",
        )
        self.create_medication_dispense(
            order=another_dispense_order,
            encounter=another_encounter,
            location=child_location,
        )
        response = self.client.get(
            self.generate_summary_url(),
            {"location": self.location.external_id, "include_children": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        for result in response.data["results"]:
            if result["encounter"]["id"] == str(self.encounter.external_id):
                self.assertEqual(result["count"], 2)
            elif result["encounter"]["id"] == str(another_encounter.external_id):
                self.assertEqual(result["count"], 1)
