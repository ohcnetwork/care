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
        self.assertIn("Cannot write supply requests", response.data["detail"])

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
        self.assertIn("Cannot write supply requests", response.data["detail"])

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
