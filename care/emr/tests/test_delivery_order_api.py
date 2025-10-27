from django.urls import reverse
from model_bakery import baker

from care.emr.resources.inventory.supply_delivery.delivery_order import (
    SupplyDeliveryOrderStatusOptions,
)
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
            ]
        )

    def create_facility_location(self, facility, **kwargs):
        from care.emr.models import FacilityLocation, FacilityLocationOrganization

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
