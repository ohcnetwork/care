from decimal import Decimal
from types import SimpleNamespace

from django.urls import reverse
from model_bakery import baker

from care.emr.api.viewsets.inventory.delivery_order import DeliveryOrderViewSet
from care.emr.models import FacilityLocation, FacilityLocationOrganization
from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.models.supply_delivery import DeliveryOrder
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)
from care.emr.resources.inventory.supply_delivery.delivery_order import (
    SupplyDeliveryOrderStatusOptions,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)
from care.emr.resources.invoice.spec import InvoiceStatusOptions
from care.emr.resources.medication.dispense.spec import MedicationDispenseStatus
from care.emr.tests.test_supply_delivery import TestSupplyDeliveryViewSetBase
from care.security.permissions.charge_item import ChargeItemPermissions
from care.security.permissions.invoice import InvoicePermissions
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions
from care.utils.tests.base import CareAPITestBase


class DeliveryOrderAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user(username="superuser")
        self.user = self.create_user(username="testuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility,
        )
        self.supplier = self.create_organization(
            name="Test Supplier", org_type="product_supplier"
        )
        self.destination = self.create_facility_location(facility=self.facility)
        self.origin = self.create_facility_location(facility=self.facility)
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_read_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_external_supply_delivery.name,
            ]
        )

    def create_facility_location(self, facility, **kwargs):
        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=self.facility_organization,
        )
        return location

    def generate_base_url(self, facility_external_id):
        return reverse(
            "delivery-order-list",
            kwargs={"facility_external_id": facility_external_id},
        )

    def generate_detail_url(self, external_id, facility_external_id):
        return reverse(
            "delivery-order-detail",
            kwargs={
                "external_id": external_id,
                "facility_external_id": facility_external_id,
            },
        )

    def create_delivery_order(self, **kwargs):
        return baker.make("emr.DeliveryOrder", **kwargs)

    def generate_delivery_order_data(self, status=None, **kwargs):
        data = {
            "name": "Test Delivery Order",
            "status": status or SupplyDeliveryOrderStatusOptions.draft.value,
            "note": "This is a test delivery order",
        }
        data.update(kwargs)
        return data

    # Test cases for create delivery order

    def test_create_delivery_order_internally_as_superuser(self):
        """Test creating a delivery order as superuser"""
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                response.data["id"],
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_delivery_order_internally_as_user_with_permission(self):
        """Test creating a delivery order as a user with permission"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                response.data["id"],
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_delivery_order_internally_as_user_without_permission(self):
        """Test creating a delivery order as a user without permission"""
        self.client.force_authenticate(user=self.user)
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write delivery orders", response.data["detail"])

    def test_create_delivery_order_externally_as_superuser(self):
        """Test creating an external delivery order as superuser"""
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            destination=self.destination.external_id,
            supplier=self.supplier.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        get_response = self.client.get(
            self.generate_detail_url(
                response.data["id"],
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_delivery_order_externally_as_user_with_permission(self):
        """Test creating an external delivery order as a user with permission"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            destination=self.destination.external_id,
            supplier=self.supplier.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                response.data["id"],
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_delivery_order_externally_as_user_without_permission(self):
        """Test creating an external delivery order as a user without permission"""
        self.client.force_authenticate(user=self.user)
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            destination=self.destination.external_id,
            supplier=self.supplier.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write delivery orders", response.data["detail"])

    def test_create_delivery_order_with_mismatched_origin_destination(self):
        """Test creating a delivery order with mismatched origin and destination facilities"""
        another_facility = self.create_facility(
            user=self.superuser, name="Another Facility"
        )
        another_location = self.create_facility_location(facility=another_facility)
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            origin=self.origin.external_id,
            destination=another_location.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "Origin and destination must be in the same facility",
            response.data["detail"],
        )

    def test_create_delivery_order_with_same_origin_and_destination(self):
        """Test creating a delivery order with same origin and destination location"""
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_base_url(self.facility.external_id)
        data = self.generate_delivery_order_data(
            origin=self.destination.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.post(url, data, format="json")
        self.assertContains(
            response,
            "Origin and destination locations must be different.",
            status_code=400,
        )

    # Testcases for update delivery order

    def test_update_internal_delivery_order_as_superuser(self):
        """Test updating a delivery order as superuser"""
        delivery_order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            note="Status updated to completed",
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                delivery_order.external_id,
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"],
            SupplyDeliveryOrderStatusOptions.completed.value,
        )

    def test_update_internal_delivery_order_as_user_with_permission(self):
        """Test updating a delivery order as a user with permission"""
        delivery_order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                delivery_order.external_id,
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"],
            SupplyDeliveryOrderStatusOptions.completed.value,
        )

    def test_update_internal_delivery_order_as_user_without_permission(self):
        """Test updating a delivery order as a user without permission"""
        delivery_order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write delivery orders", response.data["detail"])

    def test_update_external_delivery_order_as_superuser(self):
        """Test updating an external delivery order as superuser"""
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            note="Status updated to completed",
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                delivery_order.external_id,
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"],
            SupplyDeliveryOrderStatusOptions.completed.value,
        )

    def test_update_external_delivery_order_as_user_with_permission(self):
        """Test updating an external delivery order as a user with permission"""
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            supplier=self.supplier.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                delivery_order.external_id,
                self.facility.external_id,
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["status"],
            SupplyDeliveryOrderStatusOptions.completed.value,
        )

    def test_update_external_delivery_order_as_user_without_permission(self):
        """Test updating an external delivery order as a user without permission"""
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            supplier=self.supplier.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write delivery orders", response.data["detail"])

    def test_update_delivery_order_with_status_abandoned(self):
        """
        Test updating a delivery order status to abandoned
        """
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.abandoned.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            supplier=self.supplier.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Delivery order already abandoned or entered in error",
            response.data["errors"][0]["msg"],
        )

    def test_update_delivery_order_with_status_entered_in_error(self):
        """
        Test updating a delivery order status to entered in error
        """
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.entered_in_error.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        data = self.generate_delivery_order_data(
            status=SupplyDeliveryOrderStatusOptions.completed.value,
            supplier=self.supplier.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Delivery order already abandoned or entered in error",
            response.data["errors"][0]["msg"],
        )

    # Testcases for retrieve delivery order

    def test_retrieve_internal_delivery_order_as_superuser(self):
        """Test retrieving a delivery order as superuser"""
        delivery_order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(delivery_order.external_id))

    def test_retrieve_internal_delivery_order_as_user_with_permission(self):
        """Test retrieving a delivery order as a user with permission"""
        delivery_order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(delivery_order.external_id))

    def test_retrieve_internal_delivery_order_as_user_without_permission(self):
        """Test retrieving a delivery order as a user without permission"""
        delivery_order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read delivery orders", response.data["detail"])

    def test_retrieve_external_delivery_order_as_superuser(self):
        """Test retrieving an external delivery order as superuser"""
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(delivery_order.external_id))

    def test_retrieve_external_delivery_order_as_user_with_permission(self):
        """Test retrieving an external delivery order as a user with permission"""
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(delivery_order.external_id))

    def test_retrieve_external_delivery_order_as_user_without_permission(self):
        """Test retrieving an external delivery order as a user without permission"""
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_detail_url(
            delivery_order.external_id,
            self.facility.external_id,
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read delivery orders", response.data["detail"])

    # Test cases for list delivery orders

    def test_list_delivery_orders_as_superuser(self):
        """Test listing delivery orders as superuser"""
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        delivery_order2 = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )
        self.assertIn(
            str(delivery_order2.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_as_user_with_permission(self):
        """Test listing delivery orders as a user with permission"""
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        delivery_order2 = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )
        self.assertIn(
            str(delivery_order2.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_as_user_without_permission(self):
        """Test listing delivery orders as a user without permission without filters"""
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        delivery_order2 = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )
        self.assertIn(
            str(delivery_order2.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_origin_filter(self):
        """Test listing delivery orders with origin filter"""
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url, {"origin": self.origin.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_origin_filter_as_user_without_permission(self):
        """Test listing delivery orders with origin filter as user without permission"""
        self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url, {"origin": self.origin.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot list delivery orders", response.data["detail"])

    def test_list_delivery_orders_with_destination_filter(self):
        """Test listing delivery orders with destination filter"""
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        delivery_order2 = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        another_destination = self.create_facility_location(facility=self.facility)
        self.create_delivery_order(
            supplier=self.supplier,
            destination=another_destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {"destination": self.destination.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )
        self.assertIn(
            str(delivery_order2.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_destination_filter_as_user_without_permission(
        self,
    ):
        """Test listing delivery orders with destination filter as user without permission"""
        self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url, {"destination": self.destination.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot list delivery orders", response.data["detail"])

    def test_list_delivery_orders_with_status_filter(self):
        """Test listing delivery orders with status filter"""
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.completed.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {"status": SupplyDeliveryOrderStatusOptions.draft.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_supplier_filter(self):
        """Test listing delivery orders with supplier filter"""
        delivery_order2 = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        another_supplier = self.create_organization(
            name="Another Supplier", org_type="product_supplier"
        )
        self.create_delivery_order(
            supplier=another_supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {"supplier": self.supplier.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            str(delivery_order2.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_origin_include_children_filter_as_true(self):
        """Test listing delivery orders with origin include_children filter as true"""
        child_location = self.create_facility_location(
            facility=self.facility,
            parent=self.origin,
        )
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        delivery_order2 = self.create_delivery_order(
            origin=child_location,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {"origin": self.origin.external_id, "include_children": "true"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )
        self.assertIn(
            str(delivery_order2.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_origin_include_children_filter_as_false(self):
        """Test listing delivery orders with origin include_children filter as false"""
        child_location = self.create_facility_location(
            facility=self.facility,
            parent=self.origin,
        )
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.create_delivery_order(
            origin=child_location,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {"origin": self.origin.external_id, "include_children": "false"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_destination_include_children_filter_as_true(
        self,
    ):
        """Test listing delivery orders with destination include_children filter as true"""
        child_location = self.create_facility_location(
            facility=self.facility,
            parent=self.destination,
        )
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        delivery_order2 = self.create_delivery_order(
            origin=self.origin,
            destination=child_location,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {"destination": self.destination.external_id, "include_children": "true"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )
        self.assertIn(
            str(delivery_order2.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_destination_include_children_filter_as_false(
        self,
    ):
        """Test listing delivery orders with destination include_children filter as false"""
        child_location = self.create_facility_location(
            facility=self.facility,
            parent=self.destination,
        )
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.create_delivery_order(
            origin=self.origin,
            destination=child_location,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {"destination": self.destination.external_id, "include_children": "false"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_origin_isnull_filter_as_true(self):
        """Test listing delivery orders with origin isnull filter as true"""
        self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            name="Internal Delivery Order",
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        delivery_order = self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            name="External Delivery Order",
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {
                "origin_isnull": "true",
                "status": SupplyDeliveryOrderStatusOptions.draft.value,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            str(delivery_order.external_id),
            [order["id"] for order in response.data["results"]],
        )

    def test_list_delivery_orders_with_origin_isnull_filter_as_false(self):
        """Test listing delivery orders with origin isnull filter as false"""
        delivery_order1 = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            name="Internal Delivery Order",
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.create_delivery_order(
            supplier=self.supplier,
            destination=self.destination,
            name="External Delivery Order",
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.client.force_authenticate(user=self.superuser)
        url = self.generate_base_url(self.facility.external_id)
        response = self.client.get(
            url,
            {
                "origin_isnull": "false",
                "status": SupplyDeliveryOrderStatusOptions.draft.value,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(
            str(delivery_order1.external_id),
            [order["id"] for order in response.data["results"]],
        )


class DeliveryOrderCompletionAPITestCase(TestSupplyDeliveryViewSetBase):
    def complete_order(self, order):
        self.client.force_authenticate(user=self.superuser)
        return self.client.put(
            reverse(
                "delivery-order-detail",
                kwargs={
                    "external_id": order.external_id,
                    "facility_external_id": self.facility.external_id,
                },
            ),
            {
                "name": order.name,
                "status": SupplyDeliveryOrderStatusOptions.completed.value,
            },
            format="json",
        )

    def test_complete_order_rejects_unfinished_deliveries(self):
        for internal in (True, False):
            for status in (SupplyDeliveryStatusOptions.in_progress.value, "draft"):
                with self.subTest(internal=internal, status=status):
                    order = self.create_delivery_order(
                        origin=self.origin if internal else None,
                        supplier=None if internal else self.supplier,
                        destination=self.destination,
                        status=SupplyDeliveryOrderStatusOptions.in_progress.value,
                    )
                    inventory_item = (
                        self.inventory_item_origin
                        if internal
                        else self.inventory_item_destination
                    )
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=inventory_item,
                        supplied_item_quantity=Decimal(10),
                        status=SupplyDeliveryStatusOptions.completed.value,
                    )
                    unfinished_child = self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=inventory_item,
                        supplied_item_quantity=Decimal(10),
                        status=status,
                        updated_by=self.user,
                    )
                    modified_date = unfinished_child.modified_date

                    response = self.complete_order(order)

                    self.assertContains(
                        response,
                        "Finalise Deliveries before completing order",
                        status_code=400,
                    )
                    order.refresh_from_db()
                    unfinished_child.refresh_from_db()
                    self.assertEqual(
                        order.status, SupplyDeliveryOrderStatusOptions.in_progress.value
                    )
                    self.assertEqual(unfinished_child.status, status)
                    self.assertEqual(unfinished_child.updated_by_id, self.user.pk)
                    self.assertEqual(unfinished_child.modified_date, modified_date)

    def test_complete_order_preserves_cancelled_deliveries(self):
        for internal in (True, False):
            with self.subTest(internal=internal):
                order = self.create_delivery_order(
                    origin=self.origin if internal else None,
                    supplier=None if internal else self.supplier,
                    destination=self.destination,
                    status=SupplyDeliveryOrderStatusOptions.in_progress.value,
                )
                inventory_item = (
                    self.inventory_item_origin
                    if internal
                    else self.inventory_item_destination
                )
                self.create_supply_delivery(
                    order=order,
                    supplied_item=self.product,
                    supplied_inventory_item=inventory_item,
                    supplied_item_quantity=Decimal(10),
                    status=SupplyDeliveryStatusOptions.completed.value,
                )
                cancelled_children = [
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=inventory_item,
                        supplied_item_quantity=Decimal(10),
                        status=status,
                        updated_by=self.user,
                    )
                    for status in (
                        SupplyDeliveryStatusOptions.abandoned.value,
                        SupplyDeliveryStatusOptions.entered_in_error.value,
                    )
                ]
                original_audits = {
                    child.pk: (child.status, child.updated_by_id, child.modified_date)
                    for child in cancelled_children
                }

                response = self.complete_order(order)

                self.assertEqual(response.status_code, 200, response.data)
                order.refresh_from_db()
                self.assertEqual(
                    order.status, SupplyDeliveryOrderStatusOptions.completed.value
                )
                for child in cancelled_children:
                    child.refresh_from_db()
                    self.assertEqual(
                        (child.status, child.updated_by_id, child.modified_date),
                        original_audits[child.pk],
                    )

    def test_complete_order_allows_completed_children_and_ignores_deleted_children(
        self,
    ):
        for internal in (True, False):
            with self.subTest(internal=internal):
                order = self.create_delivery_order(
                    origin=self.origin if internal else None,
                    supplier=None if internal else self.supplier,
                    destination=self.destination,
                    status=SupplyDeliveryOrderStatusOptions.in_progress.value,
                )
                inventory_item = (
                    self.inventory_item_origin
                    if internal
                    else self.inventory_item_destination
                )
                for _ in range(2):
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=inventory_item,
                        supplied_item_quantity=Decimal(10),
                        status=SupplyDeliveryStatusOptions.completed.value,
                    )
                for status in (SupplyDeliveryStatusOptions.in_progress.value, "draft"):
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=inventory_item,
                        supplied_item_quantity=Decimal(10),
                        status=status,
                        deleted=True,
                    )

                response = self.complete_order(order)

                self.assertEqual(response.status_code, 200, response.data)
                order.refresh_from_db()
                self.assertEqual(
                    order.status, SupplyDeliveryOrderStatusOptions.completed.value
                )


class DeliveryOrderCancellationAPITestCase(TestSupplyDeliveryViewSetBase):
    def update_order_status(self, order, status):
        self.client.force_authenticate(user=self.superuser)
        return self.client.put(
            reverse(
                "delivery-order-detail",
                kwargs={
                    "external_id": order.external_id,
                    "facility_external_id": self.facility.external_id,
                },
            ),
            {"name": order.name, "status": status},
            format="json",
        )

    def test_cancel_internal_order_updates_all_children_and_both_inventories(self):
        for status in (
            SupplyDeliveryOrderStatusOptions.abandoned.value,
            SupplyDeliveryOrderStatusOptions.entered_in_error.value,
        ):
            with self.subTest(status=status):
                order = self.create_delivery_order(
                    origin=self.origin,
                    destination=self.destination,
                    status=SupplyDeliveryOrderStatusOptions.in_progress.value,
                )
                children = [
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=self.inventory_item_origin,
                        supplied_item_quantity=quantity,
                        status=child_status,
                    )
                    for quantity, child_status in (
                        (Decimal(50), SupplyDeliveryStatusOptions.completed.value),
                        (Decimal(25), SupplyDeliveryStatusOptions.in_progress.value),
                    )
                ]
                deleted_child = self.create_supply_delivery(
                    order=order,
                    supplied_item=self.product,
                    supplied_inventory_item=self.inventory_item_origin,
                    supplied_item_quantity=Decimal(99),
                    status=SupplyDeliveryStatusOptions.completed.value,
                    deleted=True,
                )
                product = self.create_product(facility=self.facility)
                other_origin = self.create_inventory_item(
                    product=product, location=self.origin, status="active"
                )
                other_destination = self.create_inventory_item(
                    product=product, location=self.destination, status="active"
                )
                self.create_supply_delivery(
                    order=self.delivery_order_origin_external,
                    supplied_item=product,
                    supplied_inventory_item=other_origin,
                    supplied_item_quantity=Decimal(200),
                    status=SupplyDeliveryStatusOptions.completed.value,
                )
                children.extend(
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=product,
                        supplied_inventory_item=other_origin,
                        supplied_item_quantity=quantity,
                        status=child_status,
                    )
                    for quantity, child_status in (
                        (Decimal(40), SupplyDeliveryStatusOptions.completed.value),
                        (Decimal(10), SupplyDeliveryStatusOptions.in_progress.value),
                    )
                )
                sync_inventory_item(inventory_item=self.inventory_item_destination)
                sync_inventory_item(inventory_item=other_destination)

                response = self.update_order_status(order, status)

                self.assertEqual(response.status_code, 200, response.data)
                order.refresh_from_db()
                self.assertEqual(order.status, status)
                for child in children:
                    child.refresh_from_db()
                    self.assertEqual(child.status, status)
                    self.assertEqual(child.updated_by_id, self.superuser.id)
                deleted_child.refresh_from_db()
                self.assertEqual(
                    deleted_child.status, SupplyDeliveryStatusOptions.completed.value
                )
                self.inventory_item_origin.refresh_from_db()
                self.inventory_item_destination.refresh_from_db()
                other_origin.refresh_from_db()
                other_destination.refresh_from_db()
                self.assertEqual(self.inventory_item_origin.net_content, Decimal(500))
                self.assertEqual(
                    self.inventory_item_destination.net_content, Decimal(1500)
                )
                self.assertEqual(other_origin.net_content, Decimal(200))
                self.assertEqual(other_destination.net_content, Decimal(0))

    def test_cancel_order_preserves_already_cancelled_children(self):
        for status in (
            SupplyDeliveryOrderStatusOptions.abandoned.value,
            SupplyDeliveryOrderStatusOptions.entered_in_error.value,
        ):
            with self.subTest(status=status):
                order = self.create_delivery_order(
                    origin=self.origin,
                    destination=self.destination,
                    status=SupplyDeliveryOrderStatusOptions.in_progress.value,
                )
                cancelled_children = [
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=self.inventory_item_origin,
                        supplied_item_quantity=Decimal(25),
                        status=child_status,
                        updated_by=self.user,
                    )
                    for child_status in (
                        SupplyDeliveryStatusOptions.abandoned.value,
                        SupplyDeliveryStatusOptions.entered_in_error.value,
                    )
                ]
                original_values = {
                    child.pk: (child.status, child.updated_by_id, child.modified_date)
                    for child in cancelled_children
                }
                active_child = self.create_supply_delivery(
                    order=order,
                    supplied_item=self.product,
                    supplied_inventory_item=self.inventory_item_origin,
                    supplied_item_quantity=Decimal(50),
                    status=SupplyDeliveryStatusOptions.completed.value,
                )
                sync_inventory_item(inventory_item=self.inventory_item_destination)

                response = self.update_order_status(order, status)

                self.assertEqual(response.status_code, 200, response.data)
                active_child.refresh_from_db()
                self.assertEqual(active_child.status, status)
                self.assertEqual(active_child.updated_by_id, self.superuser.pk)
                for child in cancelled_children:
                    child.refresh_from_db()
                    self.assertEqual(
                        (child.status, child.updated_by_id, child.modified_date),
                        original_values[child.pk],
                    )
                self.inventory_item_origin.refresh_from_db()
                self.inventory_item_destination.refresh_from_db()
                self.assertEqual(self.inventory_item_origin.net_content, Decimal(500))
                self.assertEqual(
                    self.inventory_item_destination.net_content, Decimal(1500)
                )

    def test_cancel_external_order_reverses_received_stock(self):
        for status in (
            SupplyDeliveryOrderStatusOptions.abandoned.value,
            SupplyDeliveryOrderStatusOptions.entered_in_error.value,
        ):
            with self.subTest(status=status):
                order = self.create_delivery_order(
                    destination=self.destination,
                    supplier=self.supplier,
                    status=SupplyDeliveryOrderStatusOptions.in_progress.value,
                )
                children = [
                    self.create_supply_delivery(
                        order=order,
                        supplied_item=self.product,
                        supplied_inventory_item=self.inventory_item_destination,
                        supplied_item_quantity=quantity,
                        status=child_status,
                    )
                    for quantity, child_status in (
                        (Decimal(50), SupplyDeliveryStatusOptions.completed.value),
                        (Decimal(25), SupplyDeliveryStatusOptions.in_progress.value),
                    )
                ]

                response = self.update_order_status(order, status)

                self.assertEqual(response.status_code, 200, response.data)
                for child in children:
                    child.refresh_from_db()
                    self.assertEqual(child.status, status)
                self.inventory_item_destination.refresh_from_db()
                self.assertEqual(
                    self.inventory_item_destination.net_content, Decimal(1500)
                )

    def test_cancel_transfer_from_destination_itself_does_not_require_stock(self):
        self.destination.parent = self.origin
        self.destination.save()
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        baker.make(
            MedicationDispense,
            item=self.inventory_item_destination,
            quantity=Decimal(1500),
            status=MedicationDispenseStatus.completed.value,
            patient=self.patient,
            encounter=encounter,
            location=self.destination,
        )
        order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.in_progress.value,
        )
        child = self.create_supply_delivery(
            order=order,
            supplied_item=self.product,
            supplied_inventory_item=self.inventory_item_destination,
            supplied_item_quantity=Decimal(50),
            status=SupplyDeliveryStatusOptions.completed.value,
        )
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(0))

        response = self.update_order_status(
            order, SupplyDeliveryOrderStatusOptions.abandoned.value
        )

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        child.refresh_from_db()
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(order.status, SupplyDeliveryOrderStatusOptions.abandoned.value)
        self.assertEqual(child.status, SupplyDeliveryStatusOptions.abandoned.value)
        self.assertEqual(self.inventory_item_origin.net_content, Decimal(500))
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(0))

    def test_cancel_order_rolls_back_when_combined_receipts_exceed_available_stock(
        self,
    ):
        order = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyDeliveryOrderStatusOptions.in_progress.value,
        )
        children = [
            self.create_supply_delivery(
                order=order,
                supplied_item=self.product,
                supplied_inventory_item=self.inventory_item_origin,
                supplied_item_quantity=quantity,
                status=SupplyDeliveryStatusOptions.completed.value,
            )
            for quantity in (Decimal(20), Decimal(30))
        ]
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        baker.make(
            MedicationDispense,
            item=self.inventory_item_destination,
            quantity=Decimal(1530),
            status=MedicationDispenseStatus.completed.value,
            patient=self.patient,
            encounter=encounter,
            location=self.destination,
        )
        sync_inventory_item(inventory_item=self.inventory_item_destination)

        response = self.update_order_status(
            order, SupplyDeliveryOrderStatusOptions.entered_in_error.value
        )

        self.assertContains(
            response, "Inventory item does not have enough stock", status_code=400
        )
        order.refresh_from_db()
        self.assertEqual(
            order.status, SupplyDeliveryOrderStatusOptions.in_progress.value
        )
        for child in children:
            child.refresh_from_db()
            self.assertEqual(child.status, SupplyDeliveryStatusOptions.completed.value)
        self.inventory_item_origin.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_origin.net_content, Decimal(450))
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(20))

    def test_repeating_cancelled_status_does_not_cascade_again(self):
        for status in (
            SupplyDeliveryOrderStatusOptions.abandoned.value,
            SupplyDeliveryOrderStatusOptions.entered_in_error.value,
        ):
            with self.subTest(status=status):
                order = self.create_delivery_order(
                    origin=self.origin,
                    destination=self.destination,
                    status=status,
                )
                child = self.create_supply_delivery(
                    order=order,
                    supplied_item=self.product,
                    supplied_inventory_item=self.inventory_item_origin,
                    supplied_item_quantity=Decimal(40),
                    status=SupplyDeliveryStatusOptions.in_progress.value,
                )

                response = self.update_order_status(order, status)

                self.assertEqual(response.status_code, 200, response.data)
                child.refresh_from_db()
                self.assertEqual(
                    child.status, SupplyDeliveryStatusOptions.in_progress.value
                )
                self.inventory_item_origin.refresh_from_db()
                self.assertEqual(self.inventory_item_origin.net_content, Decimal(460))
                child.status = SupplyDeliveryStatusOptions.abandoned.value
                child.save(update_fields=["status"])
                sync_inventory_item(inventory_item=self.inventory_item_origin)


class MedicationReturnDeliveryOrderAPITestCase(TestSupplyDeliveryViewSetBase):
    def setUp(self):
        """
        Setup for medication return delivery order test case
        Inherit setup from TestSupplyDeliveryViewSetBase
        Inventory item and product setup for destination with quantity 1500
        Medication dispense of quantity 50 created for the patient from destination inventory item


        Needs to check automatic generation of return invoice and charge item related to that account
        when the delivery order status is updated to completed and cancellation of return invoice when delivery order is abandoned or entered in error

        """
        super().setUp()
        self.return_order_destination = self.create_delivery_order(
            destination=self.destination,
            patient=self.patient,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
            name=f"{self.patient.name}-Return Delivery Order",
        )
        self.return_delivery_order_data = {
            "name": self.return_order_destination.name,
            "destination": self.return_order_destination.destination.external_id,
            "status": self.return_order_destination.status,
        }
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.return_medication = self.create_medication_dispense(
            quantity=50,
            inventory_item=self.inventory_item_destination,
        )
        self.return_delivery_order_destination = self.create_supply_delivery(
            order=self.return_order_destination,
            supplied_item_quantity=Decimal(50),
            supplied_item=self.product,
            status=SupplyDeliveryStatusOptions.completed.value,
            supplied_inventory_item=self.inventory_item_destination,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_external_supply_delivery.name,
                InvoicePermissions.can_read_invoice.name,
                InvoicePermissions.can_write_invoice.name,
                ChargeItemPermissions.can_read_charge_item.name,
            ]
        )

    def create_medication_dispense(self, quantity, inventory_item, **kwargs):
        return baker.make(
            MedicationDispense,
            item=inventory_item,
            quantity=quantity,
            status=MedicationDispenseStatus.completed.value,
            encounter=self.encounter,
            patient=self.patient,
            location=self.destination,
            **kwargs,
        )

    def generate_order_detail_url(self, external_id, facility_external_id):
        return reverse(
            "delivery-order-detail",
            kwargs={
                "external_id": external_id,
                "facility_external_id": facility_external_id,
            },
        )

    def generate_invoice_detail_url(self, external_id, facility_external_id):
        return reverse(
            "invoice-detail",
            kwargs={
                "external_id": external_id,
                "facility_external_id": facility_external_id,
            },
        )

    def test_medication_return_delivery_order_as_superuser(self):
        """
        Test creating a medication return delivery order as superuser
        Verify that return invoice is generated when delivery order status is updated to completed,
        Check that cancelled children do not affect stock or refund items.

        """
        cancelled_children = [
            self.create_supply_delivery(
                order=self.return_order_destination,
                supplied_item_quantity=Decimal(100),
                supplied_item=self.product,
                status=status,
                supplied_inventory_item=self.inventory_item_destination,
                updated_by=self.user,
            )
            for status in (
                SupplyDeliveryStatusOptions.abandoned.value,
                SupplyDeliveryStatusOptions.entered_in_error.value,
            )
        ]
        original_audits = {
            child.pk: (child.status, child.updated_by_id, child.modified_date)
            for child in cancelled_children
        }
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1500))

        get_invoice = self.client.get(
            self.generate_invoice_detail_url(
                external_id=response.data["patient_invoice_id"],
                facility_external_id=self.facility.external_id,
            )
        )
        self.assertEqual(get_invoice.status_code, 200)
        self.assertTrue(get_invoice.data["is_refund"])
        self.assertEqual(get_invoice.data["total_net"], "-5000.000000")
        self.assertEqual(len(get_invoice.data["charge_items"]), 1)
        self.assertEqual(
            get_invoice.data["charge_items"][0]["total_price"], "-5000.000000"
        )
        for child in cancelled_children:
            child.refresh_from_db()
            self.assertEqual(
                (child.status, child.updated_by_id, child.modified_date),
                original_audits[child.pk],
            )

    def test_medication_return_delivery_order_cancellation_as_superuser(self):
        """
        Test cancelling a medication return delivery order as superuser
        Cancelling the parent cancels its deliveries, reverses received stock,
        and cancels the refund invoice and charge items.
        """
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        invoice_id = response.data["patient_invoice_id"]
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.entered_in_error.value
        )
        cancel_response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(cancel_response.status_code, 200)
        get_invoice = self.client.get(
            self.generate_invoice_detail_url(
                external_id=invoice_id,
                facility_external_id=self.facility.external_id,
            )
        )
        self.assertEqual(get_invoice.status_code, 200)
        self.assertEqual(
            get_invoice.data["status"], InvoiceStatusOptions.cancelled.value
        )
        self.charge_item_id = get_invoice.data["charge_items"][0]["id"]
        get_charge_item = self.client.get(
            reverse(
                "charge_item-detail",
                kwargs={
                    "external_id": self.charge_item_id,
                    "facility_external_id": self.facility.external_id,
                },
            )
        )
        self.assertEqual(get_charge_item.status_code, 200)
        self.assertEqual(
            get_charge_item.data["status"],
            ChargeItemStatusOptions.entered_in_error.value,
        )
        self.assertEqual(get_charge_item.data["paid_invoice"], None)
        self.assertEqual(get_charge_item.data["paid_on"], None)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (Decimal(1450)))
        self.return_delivery_order_destination.refresh_from_db()
        self.assertEqual(
            self.return_delivery_order_destination.status,
            SupplyDeliveryStatusOptions.entered_in_error.value,
        )

    def test_return_cancellation_uses_refund_created_after_instance_was_loaded(self):
        stale_order = DeliveryOrder.objects.get(pk=self.return_order_destination.pk)
        self.assertIsNone(stale_order.patient_invoice)
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        completed_order = DeliveryOrder.objects.get(pk=stale_order.pk)
        invoice = completed_order.patient_invoice
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.status, InvoiceStatusOptions.issued.value)

        stale_order.status = SupplyDeliveryOrderStatusOptions.entered_in_error.value
        view = DeliveryOrderViewSet()
        view.request = SimpleNamespace(user=self.superuser, data={})
        view.perform_update(stale_order)

        self.return_order_destination.refresh_from_db()
        self.return_delivery_order_destination.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(self.return_order_destination.patient_invoice_id, invoice.pk)
        self.assertEqual(
            self.return_order_destination.status,
            SupplyDeliveryOrderStatusOptions.entered_in_error.value,
        )
        self.assertEqual(invoice.status, InvoiceStatusOptions.cancelled.value)
        charge_items = list(ChargeItem.objects.filter(id__in=invoice.charge_items))
        self.assertTrue(charge_items)
        for charge_item in charge_items:
            self.assertEqual(
                charge_item.status, ChargeItemStatusOptions.entered_in_error.value
            )
            self.assertIsNone(charge_item.paid_invoice_id)
            self.assertIsNone(charge_item.paid_on)
        self.assertEqual(
            self.return_delivery_order_destination.status,
            SupplyDeliveryStatusOptions.entered_in_error.value,
        )
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1450))

    def test_medication_return_delivery_order_as_user_without_permission(self):
        """
        Test creating a medication return delivery order as a user without permission
        Verify that user cannot update the delivery order status to completed and return invoice is not generated
        """
        self.client.force_authenticate(user=self.user)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write delivery orders", response.data["detail"])

    def test_cannot_abandon_medication_return_delivery_order(self):
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.abandoned.value
        )

        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )

        self.assertContains(
            response,
            "Cannot abandon a delivery order with medication return",
            status_code=400,
        )
        self.return_order_destination.refresh_from_db()
        self.return_delivery_order_destination.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(
            self.return_order_destination.status,
            SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.assertEqual(
            self.return_delivery_order_destination.status,
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1500))

    def test_return_cancellation_rolls_back_invoice_when_received_stock_is_unavailable(
        self,
    ):
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        invoice_id = response.data["patient_invoice_id"]
        self.create_medication_dispense(
            quantity=Decimal(1475), inventory_item=self.inventory_item_destination
        )
        sync_inventory_item(inventory_item=self.inventory_item_destination)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.entered_in_error.value
        )

        cancel_response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )

        self.assertContains(
            cancel_response,
            "Inventory item does not have enough stock",
            status_code=400,
        )
        self.return_order_destination.refresh_from_db()
        self.return_delivery_order_destination.refresh_from_db()
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(
            self.return_order_destination.status,
            SupplyDeliveryOrderStatusOptions.completed.value,
        )
        self.assertEqual(
            self.return_delivery_order_destination.status,
            SupplyDeliveryStatusOptions.completed.value,
        )
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(25))
        invoice_response = self.client.get(
            self.generate_invoice_detail_url(invoice_id, self.facility.external_id)
        )
        self.assertEqual(invoice_response.status_code, 200, invoice_response.data)
        self.assertEqual(
            invoice_response.data["status"], InvoiceStatusOptions.issued.value
        )
        self.assertEqual(
            invoice_response.data["charge_items"][0]["status"],
            ChargeItemStatusOptions.billed.value,
        )

    def test_medication_return_delivery_order_as_user_with_permission(self):
        """
        Test returning a medication return delivery order as user with permission

        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, Decimal(1500))
        get_invoice = self.client.get(
            self.generate_invoice_detail_url(
                external_id=response.data["patient_invoice_id"],
                facility_external_id=self.facility.external_id,
            )
        )
        self.assertEqual(get_invoice.status_code, 200)
        self.assertTrue(get_invoice.data["is_refund"])
        self.assertEqual(get_invoice.data["total_net"], "-5000.000000")
        self.assertEqual(
            get_invoice.data["charge_items"][0]["total_price"], "-5000.000000"
        )

    def test_medication_return_delivery_order_cancellation_as_user_with_permission(
        self,
    ):
        """
        Test cancelling a medication return delivery order as user with permission
        Cancelling the parent cancels its deliveries, reverses received stock,
        and cancels the refund invoice and charge items.
        """
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            role=self.role,
            facility_organization=self.facility_organization,
            user=self.user,
        )
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        invoice_id = response.data["patient_invoice_id"]
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.entered_in_error.value
        )
        cancel_response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )
        self.assertEqual(cancel_response.status_code, 200)
        get_invoice = self.client.get(
            self.generate_invoice_detail_url(
                external_id=invoice_id,
                facility_external_id=self.facility.external_id,
            )
        )
        self.assertEqual(get_invoice.status_code, 200)
        self.assertEqual(
            get_invoice.data["status"], InvoiceStatusOptions.cancelled.value
        )
        self.charge_item_id = get_invoice.data["charge_items"][0]["id"]
        get_charge_item = self.client.get(
            reverse(
                "charge_item-detail",
                kwargs={
                    "external_id": self.charge_item_id,
                    "facility_external_id": self.facility.external_id,
                },
            )
        )
        self.assertEqual(get_charge_item.status_code, 200)
        self.assertEqual(
            get_charge_item.data["status"],
            ChargeItemStatusOptions.entered_in_error.value,
        )
        self.assertEqual(get_charge_item.data["paid_invoice"], None)
        self.assertEqual(get_charge_item.data["paid_on"], None)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (Decimal(1450)))
        self.return_delivery_order_destination.refresh_from_db()
        self.assertEqual(
            self.return_delivery_order_destination.status,
            SupplyDeliveryStatusOptions.entered_in_error.value,
        )

    def test_complete_medication_return_order_rejects_unfinished_supply_deliveries(
        self,
    ):
        """Reject incomplete returns before changing stock or creating refund items."""
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.completed.value
        )
        invoice_count = Invoice.objects.count()
        charge_count = ChargeItem.objects.count()
        self.inventory_item_destination.refresh_from_db()
        original_stock = self.inventory_item_destination.net_content
        original_stock_modified_date = self.inventory_item_destination.modified_date
        for status in (
            SupplyDeliveryStatusOptions.in_progress.value,
            "draft",
        ):
            with self.subTest(status=status):
                self.return_delivery_order_destination.status = status
                self.return_delivery_order_destination.save(update_fields=["status"])
                child_modified_date = (
                    self.return_delivery_order_destination.modified_date
                )

                response = self.client.put(
                    self.generate_order_detail_url(
                        self.return_order_destination.external_id,
                        self.facility.external_id,
                    ),
                    self.return_delivery_order_data,
                    format="json",
                )

                self.assertContains(
                    response,
                    "Finalise Deliveries before completing order",
                    status_code=400,
                )
                self.return_order_destination.refresh_from_db()
                self.assertEqual(
                    self.return_order_destination.status,
                    SupplyDeliveryOrderStatusOptions.draft.value,
                )
                self.assertIsNone(self.return_order_destination.patient_invoice_id)
                self.assertEqual(Invoice.objects.count(), invoice_count)
                self.assertEqual(ChargeItem.objects.count(), charge_count)
                self.return_delivery_order_destination.refresh_from_db()
                self.assertEqual(self.return_delivery_order_destination.status, status)
                self.assertEqual(
                    self.return_delivery_order_destination.modified_date,
                    child_modified_date,
                )
                self.inventory_item_destination.refresh_from_db()
                self.assertEqual(
                    self.inventory_item_destination.net_content, original_stock
                )
                self.assertEqual(
                    self.inventory_item_destination.modified_date,
                    original_stock_modified_date,
                )

    def test_cancel_medication_return_delivery_order_without_generating_return_invoice(
        self,
    ):
        """
        Test cancelling a medication return delivery order without generating return invoice
        Cancelling a draft return order cancels its deliveries and reverses stock
        without creating a refund invoice.
        """
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_data["status"] = (
            SupplyDeliveryOrderStatusOptions.entered_in_error.value
        )
        cancel_response = self.client.put(
            self.generate_order_detail_url(
                self.return_order_destination.external_id, self.facility.external_id
            ),
            self.return_delivery_order_data,
            format="json",
        )

        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.data["patient_invoice_id"], None)
        self.inventory_item_destination.refresh_from_db()
        self.assertEqual(self.inventory_item_destination.net_content, (Decimal(1450)))
        self.return_delivery_order_destination.refresh_from_db()
        self.assertEqual(
            self.return_delivery_order_destination.status,
            SupplyDeliveryStatusOptions.entered_in_error.value,
        )
