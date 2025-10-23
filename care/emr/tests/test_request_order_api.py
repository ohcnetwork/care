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


class SupplyRequestAPITestCase(CareAPITestBase):
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
