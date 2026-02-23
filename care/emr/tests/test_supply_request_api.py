from decimal import Decimal
from uuid import uuid4

from django.urls import reverse
from model_bakery import baker

from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.inventory.supply_request.spec import SupplyRequestStatusOptions
from care.security.permissions.supply_request import SupplyRequestPermissions
from care.utils.tests.base import CareAPITestBase


class SupplyRequestAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.patient = self.create_patient(name="Test Patient")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility,
        )
        self.supplier = self.create_organization(name="Test Supplier")
        self.destination = self.create_facility_location(facility=self.facility)
        self.origin = self.create_facility_location(facility=self.facility)

        self.request_order_internal = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.delivery_order_internal = self.create_delivery_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.request_order_origin_external = self.create_request_order(
            supplier=self.supplier,
            destination=self.origin,
        )

        self.request_order_destination_external = self.create_request_order(
            supplier=self.supplier,
            destination=self.destination,
        )

        self.product_knowledge = baker.make(
            ProductKnowledge,
            facility=self.facility,
            slug=f"f-{self.facility.external_id}-product-knowledge",
        )

        self.base_url = reverse("supply_request-list")
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyRequestPermissions.can_write_supply_request.name,
                SupplyRequestPermissions.can_read_supply_request.name,
            ]
        )
        self.request_order_url = reverse("supply_request-request-orders")

    def generate_supply_request_data(
        self, quantity=None, item=None, status=None, **kwargs
    ):
        data = {
            "status": status or SupplyRequestStatusOptions.active,
            "quantity": quantity or 100,
            "item": item or str(self.product_knowledge.external_id),
            **kwargs,
        }
        data.update(kwargs)
        return data

    def create_request_order(self, **kwargs):
        return baker.make("emr.RequestOrder", name="Test Request Order", **kwargs)

    def create_supply_request(self, status=None, **kwargs):
        return baker.make(
            "emr.SupplyRequest",
            status=status or SupplyRequestStatusOptions.active,
            item=self.product_knowledge,
            **kwargs,
        )

    def get_detail_url(self, external_id):
        return reverse("supply_request-detail", kwargs={"external_id": external_id})

    def create_facility_location(self, facility, **kwargs):
        from care.emr.models import FacilityLocation, FacilityLocationOrganization

        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=self.facility_organization,
        )
        return location

    def create_delivery_order(self, **kwargs):
        from care.emr.models import DeliveryOrder

        return baker.make(DeliveryOrder, **kwargs)

    def create_supply_delivery(self, **kwargs):
        from care.emr.models import SupplyDelivery

        return baker.make(SupplyDelivery, **kwargs)

    # Test cases for create supply request

    def test_create_supply_request_as_superuser(self):
        """Test creating a supply request as a superuser"""

        self.client.force_authenticate(user=self.superuser)
        data = self.generate_supply_request_data(
            order=str(self.request_order_internal.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(
            Decimal(get_response.data["quantity"]), Decimal(data["quantity"])
        )
        self.assertEqual(
            get_response.data["item"]["id"], str(self.product_knowledge.external_id)
        )

    def test_create_supply_request_as_user_with_permissions(self):
        """Test creating a supply request as a user with permissions"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            order=str(self.request_order_internal.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(
            Decimal(get_response.data["quantity"]), Decimal(data["quantity"])
        )
        self.assertEqual(
            get_response.data["item"]["id"], str(self.product_knowledge.external_id)
        )

    def test_create_supply_request_for_internal_as_user_without_permissions(self):
        """Test creating a supply request as a user without permissions"""
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            order=str(self.request_order_internal.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", str(response.data))

    def test_create_supply_request_without_order(self):
        """Test creating a supply request without an order"""
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_supply_request_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_supply_request_with_invalid_item(self):
        """Test creating a supply request with an invalid item"""
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_supply_request_data(
            item=uuid4(), order=str(self.request_order_internal.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "No ProductKnowledge matches the given query.", str(response.data)
        )

    def test_create_supply_request_for_origin_externally_as_user_with_permissions(self):
        """Test creating a supply request for an origin externally as a user with permissions"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            order=str(self.request_order_origin_external.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(
            Decimal(get_response.data["quantity"]), Decimal(data["quantity"])
        )
        self.assertEqual(
            get_response.data["item"]["id"], str(self.product_knowledge.external_id)
        )

    def test_create_supply_request_for_origin_externally_as_user_without_permissions(
        self,
    ):
        """Test creating a supply request for an origin externally as a user without permissions"""
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            order=str(self.request_order_origin_external.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", str(response.data))

    def test_create_supply_request_for_destination_externally_with_permissions(self):
        """Test creating a supply request for a destination externally with permissions"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            order=str(self.request_order_destination_external.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        get_response = self.client.get(
            self.get_detail_url(response.data["id"]), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["status"], data["status"])
        self.assertEqual(
            Decimal(get_response.data["quantity"]), Decimal(data["quantity"])
        )
        self.assertEqual(
            get_response.data["item"]["id"], str(self.product_knowledge.external_id)
        )

    def test_create_supply_request_for_destination_externally_without_permission(self):
        """Test creating a supply request for a destination externally without permission"""
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            order=str(self.request_order_destination_external.external_id)
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", str(response.data))

    # Test cases for retrieve supply request

    def test_retrieve_supply_request_as_superuser(self):
        """Test retrieving a supply request as a superuser"""
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(supply_request.external_id))

    def test_retrieve_supply_request_internal_as_user_with_permissions(self):
        """Test retrieving a supply request as a user with permissions"""
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(supply_request.external_id))

    def test_retrieve_supply_request_internal_as_user_without_permissions(self):
        """Test retrieving a supply request as a user without permissions"""
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read supply requests", str(response.data))

    def test_retrieve_supply_request_for_origin_externally_with_permission(self):
        """Test retrieving a supply request for an origin externally with permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_origin_external,
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(supply_request.external_id))

    def test_retrieve_supply_request_for_origin_externally_without_permission(self):
        """Test retrieving a supply request for an origin externally without permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_origin_external,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read supply requests", str(response.data))

    def test_retrieve_supply_request_for_destination_externally_with_permission(self):
        """Test retrieving a supply request for a destination externally with permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_destination_external,
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(supply_request.external_id))

    def test_retrieve_supply_request_for_destination_externally_without_permission(
        self,
    ):
        """Test retrieving a supply request for a destination externally without permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_destination_external,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read supply requests", str(response.data))

    # Test cases for update supply request

    def test_update_supply_request_as_superuser(self):
        """Test updating a supply request as a superuser"""
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
            quantity=100,
        )
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_supply_request_data(
            quantity=Decimal(200),
            order=str(self.request_order_origin_external.external_id),
        )
        response = self.client.patch(
            self.get_detail_url(supply_request.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(supply_request.external_id), format="json"
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], str(supply_request.external_id))
        self.assertEqual(Decimal(get_response.data["quantity"]), Decimal(200))

    def test_update_supply_request_internally_as_user_with_permissions(self):
        """Test updating a supply request as a user with permissions"""
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
            quantity=Decimal(100),
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            quantity=Decimal(200),
            order=str(self.request_order_origin_external.external_id),
        )
        response = self.client.patch(
            self.get_detail_url(supply_request.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["quantity"]), Decimal(200))

    def test_update_supply_request_internally_as_user_without_permissions(self):
        """Test updating a supply request as a user without permissions"""
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
            quantity=100,
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            quantity=200, order=str(self.request_order_origin_external.external_id)
        )
        response = self.client.patch(
            self.get_detail_url(supply_request.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", str(response.data))

    def test_update_supply_request_for_origin_externally_with_permission(self):
        """Test updating a supply request for an origin externally with permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_origin_external,
            quantity=Decimal(100),
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            quantity=Decimal(200), order=str(self.request_order_internal.external_id)
        )
        response = self.client.patch(
            self.get_detail_url(supply_request.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["quantity"]), Decimal(200))

    def test_update_supply_request_for_origin_externally_without_permission(self):
        """Test updating a supply request for an origin externally without permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_origin_external,
            quantity=100,
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            quantity=200, order=str(self.request_order_internal.external_id)
        )
        response = self.client.patch(
            self.get_detail_url(supply_request.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", str(response.data))

    def test_update_supply_request_for_destination_externally_with_permission(self):
        """Test updating a supply request for a destination externally with permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_destination_external,
            quantity=100,
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            quantity=200, order=str(self.request_order_internal.external_id)
        )
        response = self.client.patch(
            self.get_detail_url(supply_request.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["quantity"], "200")

    def test_update_supply_request_for_destination_externally_without_permission(self):
        """Test updating a supply request for a destination externally without permission"""
        supply_request = self.create_supply_request(
            order=self.request_order_destination_external,
            quantity=100,
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_supply_request_data(
            quantity=200, order=str(self.request_order_internal.external_id)
        )
        response = self.client.patch(
            self.get_detail_url(supply_request.external_id), data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", str(response.data))

    # Test cases for list supply requests

    def test_list_supply_requests_as_superuser_with_order_filter(self):
        """Test listing supply requests as a superuser with order filter"""
        supply_request1 = self.create_supply_request(
            order=self.request_order_internal,
        )
        supply_request2 = self.create_supply_request(order=self.request_order_internal)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.base_url,
            {"order": str(self.request_order_internal.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        external_ids = [supply_request1.external_id, supply_request2.external_id]
        for item in response.data["results"]:
            self.assertIn(item["id"], map(str, external_ids))

    def test_list_supply_requests_with_order_filter_as_user_with_permissions(self):
        """Test listing supply requests as a user with permissions and order filter"""
        supply_request1 = self.create_supply_request(
            order=self.request_order_internal,
        )
        supply_request2 = self.create_supply_request(order=self.request_order_internal)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {"order": str(self.request_order_internal.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        external_ids = [supply_request1.external_id, supply_request2.external_id]
        for item in response.data["results"]:
            self.assertIn(item["id"], map(str, external_ids))

    def test_list_supply_requests_as_user_without_permissions(self):
        """Test listing supply requests as a user without permissions"""
        self.create_supply_request(
            order=self.request_order_internal,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {"order": str(self.request_order_internal.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read supply requests", str(response.data))

    def test_list_supply_requests_without_filter(self):
        """Test listing supply requests without any filter"""
        self.create_supply_request(
            order=self.request_order_internal,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("No filters provided", str(response.data))

    def test_list_supply_requests_for_origin_externally_without_permission(self):
        """Test listing supply requests for an origin externally without permission with order filter"""
        self.create_supply_request(
            order=self.request_order_origin_external,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {"order": str(self.request_order_origin_external.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read supply requests", str(response.data))

    def test_list_supply_requests_for_destination_externally_without_permission(self):
        """Test listing supply requests for a destination externally without permission with order filter"""
        self.create_supply_request(
            order=self.request_order_destination_external,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {"order": str(self.request_order_destination_external.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read supply requests", str(response.data))

    def test_list_supply_request_with_origin_filter(self):
        """Test listing supply requests with origin filter"""
        supply_request1 = self.create_supply_request(
            order=self.request_order_internal,
        )
        self.create_supply_request(order=self.request_order_destination_external)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url, {"origin": str(self.origin.external_id)}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_request1.external_id)
        )

    def test_list_supply_request_with_destination_filter(self):
        """Test listing supply requests with destination filter"""
        self.create_supply_request(
            order=self.request_order_origin_external,
        )
        supply_request2 = self.create_supply_request(order=self.request_order_internal)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {"destination": str(self.destination.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_request2.external_id)
        )

    def test_list_supply_request_with_origin_filter_without_permission(self):
        """Test listing supply requests with origin filter without permission"""
        self.create_supply_request(
            order=self.request_order_internal,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url, {"origin": str(self.origin.external_id)}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot list supply requests", str(response.data))

    def test_list_supply_request_with_destination_filter_without_permission(self):
        """Test listing supply requests with destination filter without permission"""
        self.create_supply_request(
            order=self.request_order_internal,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {"destination": str(self.destination.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot list supply requests", str(response.data))

    def test_list_supply_request_with_origin_filter_and_include_children_as_true(self):
        """Test listing supply requests with origin filter and include children as true"""
        child_location = self.create_facility_location(
            facility=self.facility, parent=self.origin
        )
        child_request_order = self.create_request_order(
            origin=child_location,
            destination=self.destination,
        )
        supply_request_child = self.create_supply_request(
            order=child_request_order,
        )
        supply_request1 = self.create_supply_request(
            order=self.request_order_internal,
        )

        self.create_supply_request(order=self.request_order_destination_external)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "origin": str(self.origin.external_id),
                "include_children": "true",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_request1.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(supply_request_child.external_id)
        )

    def test_list_supply_request_with_origin_filter_and_include_children_as_false(self):
        """Test listing supply requests with origin filter and include children as false"""
        child_location = self.create_facility_location(
            facility=self.facility, parent=self.origin
        )
        child_request_order = self.create_request_order(
            origin=child_location,
            destination=self.destination,
        )
        self.create_supply_request(
            order=child_request_order,
        )
        supply_request1 = self.create_supply_request(
            order=self.request_order_internal,
        )

        self.create_supply_request(order=self.request_order_destination_external)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "origin": str(self.origin.external_id),
                "include_children": "false",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_request1.external_id)
        )

    def test_list_supply_request_with_destination_filter_and_include_children_as_true(
        self,
    ):
        """Test listing supply requests with destination filter and include children as true"""
        child_location = self.create_facility_location(
            facility=self.facility, parent=self.destination
        )
        child_request_order = self.create_request_order(
            origin=self.origin,
            destination=child_location,
        )
        supply_request_child = self.create_supply_request(
            order=child_request_order,
        )
        supply_request2 = self.create_supply_request(
            order=self.request_order_internal,
        )

        self.create_supply_request(order=self.request_order_origin_external)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "destination": str(self.destination.external_id),
                "include_children": "true",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_request2.external_id)
        )
        self.assertEqual(
            response.data["results"][1]["id"], str(supply_request_child.external_id)
        )

    def test_list_supply_request_with_destination_filter_and_include_children_as_false(
        self,
    ):
        """Test listing supply requests with destination filter and include children as false"""
        child_location = self.create_facility_location(
            facility=self.facility, parent=self.destination
        )
        child_request_order = self.create_request_order(
            origin=self.origin,
            destination=child_location,
        )
        self.create_supply_request(
            order=child_request_order,
        )
        supply_request2 = self.create_supply_request(
            order=self.request_order_internal,
        )

        self.create_supply_request(order=self.request_order_origin_external)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.base_url,
            {
                "destination": str(self.destination.external_id),
                "include_children": "false",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(supply_request2.external_id)
        )

    # Test case for request orders endpoint

    # We need to create a supply request and supply delivery linked to that request
    # Then we can test the request orders endpoint to retrieve the request orders
    # associated with a given delivery order.

    def test_retrive_supply_delivery_request_orders_as_superuser(self):
        """Test retrieving supply delivery related request orders as superuser"""
        self.client.force_authenticate(user=self.superuser)
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
            status=SupplyRequestStatusOptions.completed,
        )
        self.create_supply_delivery(
            order=self.delivery_order_internal,
            supply_request=supply_request,
        )
        response = self.client.get(
            self.request_order_url,
            {"delivery_order": str(self.delivery_order_internal.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.request_order_internal.external_id),
        )

    def test_retrive_supply_delivery_request_orders_without_delivery_order(self):
        """Test retrieving supply delivery related request orders without delivery order"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.request_order_url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("delivery_order is required", str(response.data))

    def test_retrive_supply_delivery_request_orders_as_user_with_permissions(self):
        """Test retrieving supply delivery related request orders as user with permissions"""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
            status=SupplyRequestStatusOptions.completed,
        )
        self.create_supply_delivery(
            order=self.delivery_order_internal,
            supply_request=supply_request,
        )
        response = self.client.get(
            self.request_order_url,
            {"delivery_order": str(self.delivery_order_internal.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.request_order_internal.external_id),
        )

    def test_retrive_supply_delivery_request_orders_as_user_without_permissions(self):
        """Test retrieving supply delivery related request orders as user without permissions"""
        self.client.force_authenticate(user=self.user)
        supply_request = self.create_supply_request(
            order=self.request_order_internal,
            status=SupplyRequestStatusOptions.completed,
        )
        self.create_supply_delivery(
            order=self.delivery_order_internal,
            supply_request=supply_request,
        )
        response = self.client.get(
            self.request_order_url,
            {"delivery_order": str(self.delivery_order_internal.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read supply requests", str(response.data))
