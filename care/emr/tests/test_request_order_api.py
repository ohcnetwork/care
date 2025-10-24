from django.urls import reverse
from model_bakery import baker

from care.emr.resources.inventory.supply_request.request_order import (
    SupplyRequestCategoryOptions,
    SupplyRequestIntentOptions,
    SupplyRequestOrderStatusOptions,
    SupplyRequestPriorityOptions,
    SupplyRequestReason,
)
from care.security.permissions.supply_request import SupplyRequestPermissions
from care.utils.tests.base import CareAPITestBase


class RequestOrderAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user(username="superuser")
        self.user = self.create_user(username="testuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility,
        )
        self.supplier = self.create_organization(name="Test Supplier")
        self.destination = self.create_facility_location(facility=self.facility)
        self.origin = self.create_facility_location(facility=self.facility)
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyRequestPermissions.can_read_supply_request.name,
                SupplyRequestPermissions.can_write_supply_request.name,
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
            "request-order-list",
            kwargs={"facility_external_id": facility_external_id},
        )

    def generate_detail_url(self, external_id, facility_external_id):
        return reverse(
            "request-order-detail",
            kwargs={
                "external_id": external_id,
                "facility_external_id": facility_external_id,
            },
        )

    def generate_request_order_data(self, **kwargs):
        return {
            "name": "Test Request Order",
            "status": kwargs.get("status", SupplyRequestOrderStatusOptions.draft.value),
            "priority": kwargs.get(
                "priority", SupplyRequestPriorityOptions.routine.value
            ),
            "intent": kwargs.get("intent", SupplyRequestIntentOptions.order.value),
            "reason": kwargs.get("reason", SupplyRequestReason.patient_care.value),
            "category": kwargs.get(
                "category", SupplyRequestCategoryOptions.central.value
            ),
            "note": kwargs.get("note", "This is a test request order."),
            **kwargs,
        }

    def create_request_order(
        self, origin=None, destination=None, supplier=None, **kwargs
    ):
        data = self.generate_request_order_data(**kwargs)
        return baker.make(
            "emr.RequestOrder",
            **data,
            origin=origin,
            destination=destination,
            supplier=supplier,
        )

    # Test cases for create request order

    def test_create_request_order_as_superuser(self):
        """Test creating a request order as a superuser."""

        self.client.force_authenticate(user=self.superuser)
        data = self.generate_request_order_data(
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.post(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                external_id=response.data["id"],
                facility_external_id=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(
            get_response.data["status"], SupplyRequestOrderStatusOptions.draft.value
        )
        self.assertEqual(
            get_response.data["priority"], SupplyRequestPriorityOptions.routine.value
        )

    def test_create_request_order_as_user_with_permission(self):
        """Test creating a request order as a user with permission."""

        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        data = self.generate_request_order_data(
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.post(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.generate_detail_url(
                external_id=response.data["id"],
                facility_external_id=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["name"], data["name"])
        self.assertEqual(
            get_response.data["status"], SupplyRequestOrderStatusOptions.draft.value
        )
        self.assertEqual(
            get_response.data["priority"], SupplyRequestPriorityOptions.routine.value
        )

    def test_create_request_order_as_user_without_permission(self):
        """Test creating a request order as a user without permission."""

        self.client.force_authenticate(user=self.user)
        data = self.generate_request_order_data(
            origin=self.origin.external_id,
            destination=self.destination.external_id,
        )
        response = self.client.post(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", response.data["detail"])

    def test_create_request_order_with_mismatched_origin_destination_facility(self):
        """Test creating a request order with mismatched origin and destination facility."""

        other_facility = self.create_facility(user=self.superuser)
        other_location = self.create_facility_location(facility=other_facility)
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_request_order_data(
            origin=self.origin.external_id,
            destination=other_location.external_id,
        )
        response = self.client.post(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "Origin and destination must be in the same facility",
            response.data["detail"],
        )

    def test_create_request_order_with_invalid_supplier_type(self):
        """Test creating a request order with an invalid supplier organization type."""

        non_supplier_org = self.create_organization(
            name="Non Supplier Org",
            org_type="hospital",
        )
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_request_order_data(
            destination=self.destination.external_id,
            supplier=non_supplier_org.external_id,
        )
        response = self.client.post(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Supplier organization must be of type product_supplier",
            status_code=400,
        )

    # Test cases for retrieve request order

    def test_retrieve_request_order_as_superuser(self):
        """Test retrieving a request order as a superuser."""

        request_order = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            supplier=self.supplier,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_detail_url(
                external_id=request_order.external_id,
                facility_external_id=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], request_order.name)
        self.assertEqual(response.data["status"], request_order.status)
        self.assertEqual(response.data["priority"], request_order.priority)

    def test_retrieve_request_order_as_user_with_permission(self):
        """Test retrieving a request order as a user with permission."""

        request_order = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            supplier=self.supplier,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.generate_detail_url(
                external_id=request_order.external_id,
                facility_external_id=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], request_order.name)
        self.assertEqual(response.data["status"], request_order.status)
        self.assertEqual(response.data["priority"], request_order.priority)

    def test_retrieve_request_order_internal_as_user_without_permission(self):
        """Test retrieving a request order as a user without permission."""

        request_order = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_detail_url(
                external_id=request_order.external_id,
                facility_external_id=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read request orders", response.data["detail"])

    def test_retrieve_request_order_destination_external_as_user_without_permission(
        self,
    ):
        """Test retrieving a request order with destination external as a user without permission."""

        request_order = self.create_request_order(
            supplier=self.supplier,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_detail_url(
                external_id=request_order.external_id,
                facility_external_id=self.facility.external_id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot read request orders", response.data["detail"])

    # Test cases for update request order

    def test_update_request_order_as_superuser(self):
        """Test updating a request order as a superuser."""
        request_order = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = self.generate_request_order_data(
            name="Updated Request Order",
            status=SupplyRequestOrderStatusOptions.completed.value,
        )
        response = self.client.patch(
            self.generate_detail_url(
                external_id=request_order.external_id,
                facility_external_id=self.facility.external_id,
            ),
            data=update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], update_data["name"])
        self.assertEqual(response.data["status"], update_data["status"])

    def test_update_request_order_as_user_with_permission(self):
        """Test updating a request order as a user with permission."""
        request_order = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        update_data = self.generate_request_order_data(
            name="Updated Request Order",
            status=SupplyRequestOrderStatusOptions.completed.value,
        )
        response = self.client.patch(
            self.generate_detail_url(
                external_id=request_order.external_id,
                facility_external_id=self.facility.external_id,
            ),
            data=update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], update_data["name"])
        self.assertEqual(response.data["status"], update_data["status"])

    def test_update_request_order_as_user_without_permission(self):
        """Test updating a request order as a user without permission."""
        request_order = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.generate_request_order_data(
            name="Updated Request Order",
            status=SupplyRequestOrderStatusOptions.completed.value,
        )
        response = self.client.patch(
            self.generate_detail_url(
                external_id=request_order.external_id,
                facility_external_id=self.facility.external_id,
            ),
            data=update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot write supply requests", response.data["detail"])

    # Test cases for list request orders

    def test_list_request_orders_as_superuser(self):
        """Test listing request orders as a superuser."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        request_order2 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        external_ids = [ro["id"] for ro in response.data["results"]]
        self.assertIn(str(request_order1.external_id), external_ids)
        self.assertIn(str(request_order2.external_id), external_ids)

    def test_list_request_orders_as_user_with_permission(self):
        """Test listing request orders as a user with permission."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        request_order2 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        external_ids = [ro["id"] for ro in response.data["results"]]
        self.assertIn(str(request_order1.external_id), external_ids)
        self.assertIn(str(request_order2.external_id), external_ids)

    def test_list_request_orders_as_user_without_permission(self):
        """
        Test listing request orders as a user without permission.
        General listing does not require permission.
        """
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        request_order2 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        external_ids = [ro["id"] for ro in response.data["results"]]
        for ro in response.data["results"]:
            external_ids.append(ro["id"])
        self.assertIn(str(request_order1.external_id), external_ids)
        self.assertIn(str(request_order2.external_id), external_ids)

    def test_list_request_orders_filtered_based_on_origin_as_user_with_permission(self):
        """Test listing request orders filtered based on origin as a user with permission."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        request_order2 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"origin": str(self.origin.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        external_ids = [ro["id"] for ro in response.data["results"]]
        for ro in response.data["results"]:
            external_ids.append(ro["id"])
        self.assertIn(str(request_order1.external_id), external_ids)
        self.assertIn(str(request_order2.external_id), external_ids)

    def test_list_request_orders_filtered_based_on_origin_as_user_without_permission(
        self,
    ):
        """Test listing request orders filtered based on origin as a user without permission."""
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"origin": str(self.origin.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot list supply requests", response.data["detail"])

    def test_list_request_orders_filtered_based_on_destination_as_user_with_permission(
        self,
    ):
        """Test listing request orders filtered based on destination as a user with permission."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        request_order2 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"destination": str(self.destination.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        external_ids = [ro["id"] for ro in response.data["results"]]
        for ro in response.data["results"]:
            external_ids.append(ro["id"])
        self.assertIn(str(request_order1.external_id), external_ids)
        self.assertIn(str(request_order2.external_id), external_ids)

    def test_list_request_orders_filtered_based_on_destination_as_user_without_permission(
        self,
    ):
        """Test listing request orders filtered based on destination as a user without permission."""
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"destination": str(self.destination.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot list supply requests", response.data["detail"])

    def test_list_request_orders_with_status_filter(self):
        """Test listing request orders with status filter."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyRequestOrderStatusOptions.draft.value,
        )
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            status=SupplyRequestOrderStatusOptions.completed.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"status": SupplyRequestOrderStatusOptions.draft.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order1.external_id)
        )

    def test_list_request_orders_with_date_filter(self):
        """Test listing request orders with date filter."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        request_order2 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"created_date__date": request_order1.created_date.date().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][1]["id"], str(request_order1.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order2.external_id)
        )

    def test_list_request_orders_with_priority_filter(self):
        """Test listing request orders with priority filter."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            priority=SupplyRequestPriorityOptions.routine.value,
        )
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            priority=SupplyRequestPriorityOptions.urgent.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"priority": SupplyRequestPriorityOptions.routine.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order1.external_id)
        )

    def test_list_request_orders_with_intent_filter(self):
        """Test listing request orders with intent filter."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            intent=SupplyRequestIntentOptions.order.value,
        )
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            intent=SupplyRequestIntentOptions.plan.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"intent": SupplyRequestIntentOptions.order.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order1.external_id)
        )

    def test_list_request_orders_with_reason_filter(self):
        """Test listing request orders with reason filter."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            reason=SupplyRequestReason.patient_care.value,
        )
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            reason=SupplyRequestReason.ward_stock.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"reason": SupplyRequestReason.patient_care.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order1.external_id)
        )

    def test_list_request_orders_with_category_filter(self):
        """Test listing request orders with category filter."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.central.value,
        )
        self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.nonstock.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"category": SupplyRequestCategoryOptions.central.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order1.external_id)
        )

    def test_list_request_orders_with_included_children_as_true_for_origin(self):
        """Test listing request orders with included children as true for origin."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.central.value,
        )
        child_facility_location = self.create_facility_location(
            name="Child Facility",
            parent=self.origin,
            facility=self.facility,
        )
        request_order2 = self.create_request_order(
            origin=child_facility_location,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.nonstock.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"include_children": "true", "origin": str(self.origin.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][1]["id"], str(request_order1.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order2.external_id)
        )

    def test_list_request_orders_with_included_children_as_false_for_origin(self):
        """Test listing request orders with included children as false for origin."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.central.value,
        )
        child_facility_location = self.create_facility_location(
            name="Child Facility",
            parent=self.origin,
            facility=self.facility,
        )
        self.create_request_order(
            name="Child Request Order",
            origin=child_facility_location,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.nonstock.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {"include_children": "false", "origin": str(self.origin.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order1.external_id)
        )

    def test_list_request_orders_with_included_children_as_true_for_destination(self):
        """Test listing request orders with included children as true for destination."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.central.value,
        )
        child_facility_location = self.create_facility_location(
            name="Child Facility",
            parent=self.destination,
            facility=self.facility,
        )
        request_order2 = self.create_request_order(
            origin=self.origin,
            destination=child_facility_location,
            category=SupplyRequestCategoryOptions.nonstock.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {
                "include_children": "true",
                "destination": str(self.destination.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][1]["id"], str(request_order1.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order2.external_id)
        )

    def test_list_request_orders_with_included_children_as_false_for_destination(self):
        """Test listing request orders with included children as false for destination."""
        request_order1 = self.create_request_order(
            origin=self.origin,
            destination=self.destination,
            category=SupplyRequestCategoryOptions.central.value,
        )
        child_facility_location = self.create_facility_location(
            name="Child Facility",
            parent=self.destination,
            facility=self.facility,
        )
        self.create_request_order(
            name="Child Request Order",
            origin=self.origin,
            destination=child_facility_location,
            category=SupplyRequestCategoryOptions.nonstock.value,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.generate_base_url(facility_external_id=self.facility.external_id),
            {
                "destination": str(self.destination.external_id),
                "include_children": "false",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(request_order1.external_id)
        )
