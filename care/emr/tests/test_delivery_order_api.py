from decimal import Decimal

from django.urls import reverse
from model_bakery import baker

from care.emr.models import FacilityLocation, FacilityLocationOrganization
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
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
        Check the inventory item restored with the return net content

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

    def test_medication_return_delivery_order_cancellation_as_superuser(self):
        """
        Test cancelling a medication return delivery order as superuser
        Verify that return invoice is cancelled when delivery order status is updated to abandoned or entered in error,
        Check the inventory item net content after cancellation remains the same
        Supply Delivery need to be updated to entered in error before updating delivery order status to abandoned
        as the inventory item is recalculated based on the supply delivery status.
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
        self.return_delivery_order_destination.status = (
            SupplyDeliveryStatusOptions.entered_in_error.value
        )
        self.return_delivery_order_destination.save(update_fields=["status"])
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
        Verify that return invoice is cancelled when delivery order status is updated to abandoned or entered in error,
        Check the inventory item net content after cancellation remains the same
        Supply Delivery need to be updated to entered in error before updating delivery order status to abandoned
        as the inventory item is recalculated based on the supply delivery status.
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
        self.return_delivery_order_destination.status = (
            SupplyDeliveryStatusOptions.entered_in_error.value
        )
        self.return_delivery_order_destination.save(update_fields=["status"])
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

    def test_create_medication_return_delivery_order_with_in_progress_supply_delivery(
        self,
    ):
        """
        Test creating a medication return delivery order with in-progress supply delivery
        Verify that delivery order cannot be marked as completed and return invoice is not generated until the supply delivery is completed
        """
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_destination.status = (
            SupplyDeliveryStatusOptions.in_progress.value
        )
        self.return_delivery_order_destination.save(update_fields=["status"])
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
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Finalise Deliveries before completing order",
            response.data["errors"][0]["msg"],
        )

    def test_cancel_medication_return_delivery_order_without_generating_return_invoice(
        self,
    ):
        """
        Test cancelling a medication return delivery order without generating return invoice
        Verify that delivery order can be marked as abandoned without generating return invoice when the order is not marked as completed
        Check the inventory item net content after cancellation remains the same
        """
        self.client.force_authenticate(user=self.superuser)
        self.return_delivery_order_destination.status = (
            SupplyDeliveryStatusOptions.entered_in_error.value
        )
        self.return_delivery_order_destination.save(update_fields=["status"])
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
