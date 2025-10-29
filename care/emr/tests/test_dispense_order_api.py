from django.urls import reverse
from model_bakery import baker

from care.emr.models.medication_dispense import DispenseOrder
from care.emr.resources.medication.dispense.dispense_order import (
    MedicationDispenseOrderStatusOptions,
)
from care.security.permissions.medication import MedicationPermissions
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions
from care.utils.tests.base import CareAPITestBase


class DispenseOrderAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user(username="superuser")
        self.user = self.create_user(username="testuser")
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.superuser, name="Test Facility")
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Org"
        )
        self.location = self.create_facility_location(
            self.facility,
            name="Pharmacy",
            facility_organization=self.facility_organization,
        )

        self.dispense_order_data = {
            "status": MedicationDispenseOrderStatusOptions.draft,
            "name": "Dispense Order",
            "note": "This is a test dispense order",
            "patient": str(self.patient.external_id),
            "location": str(self.location.external_id),
        }
        self.role = self.create_role_with_permissions(
            permissions=[
                SupplyDeliveryPermissions.can_read_supply_delivery.name,
                SupplyDeliveryPermissions.can_write_supply_delivery.name,
            ]
        )
        self.pharmacist_role = self.create_role_with_permissions(
            permissions=[
                MedicationPermissions.is_pharmacist.name,
            ]
        )

    def create_facility_location(self, facility, facility_organization, **kwargs):
        from care.emr.models import FacilityLocation, FacilityLocationOrganization

        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    def create_dispense_order(self, **kwargs):
        return baker.make(DispenseOrder, **kwargs)

    def generate_base_url(self, facility_external_id):
        return reverse(
            "dispense_order-list",
            kwargs={"facility_external_id": str(facility_external_id)},
        )

    def get_detail_url(self, facility_external_id, dispense_order_external_id):
        return reverse(
            "dispense_order-detail",
            kwargs={
                "facility_external_id": str(facility_external_id),
                "external_id": str(dispense_order_external_id),
            },
        )

    # Testcases for creating dispense order

    def test_create_dispense_order_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.generate_base_url(self.facility.external_id),
            data=self.dispense_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])
        self.assertEqual(get_response.data["name"], self.dispense_order_data["name"])

    def test_create_dispense_order_as_pharmacist(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.pharmacist_role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.generate_base_url(self.facility.external_id),
            data=self.dispense_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_dispense_order_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.generate_base_url(self.facility.external_id),
            data=self.dispense_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create dispense order",
            response.data["detail"],
        )

    def test_create_dispense_order_as_user_with_location_write_permission(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.generate_base_url(self.facility.external_id),
            data=self.dispense_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_dispense_order_in_location_of_different_facility(self):
        other_facility = self.create_facility(
            user=self.superuser, name="Other Facility"
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.generate_base_url(other_facility.external_id),
            data=self.dispense_order_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Location must be in the same facility", response.data["errors"][0]["msg"]
        )

    # Testcases for updating dispense order

    def test_update_dispense_order_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Initial Dispense Order",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        update_data = {
            "name": "Updated Dispense Order",
            "status": MedicationDispenseOrderStatusOptions.completed,
        }
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            data=update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_reposense = self.client.get(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            format="json",
        )
        self.assertEqual(get_reposense.status_code, 200)
        self.assertEqual(get_reposense.data["id"], str(dispense_order.external_id))
        self.assertEqual(get_reposense.data["name"], update_data["name"])
        self.assertEqual(get_reposense.data["status"], update_data["status"])

    def test_update_dispense_order_as_user_without_permission(self):
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Initial Dispense Order",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Dispense Order",
            "status": MedicationDispenseOrderStatusOptions.completed,
        }
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            data=update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update dispense order",
            response.data["detail"],
        )

    def test_update_dispense_order_as_user_with_location_write_permission(self):
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Initial Dispense Order",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Dispense Order",
            "status": MedicationDispenseOrderStatusOptions.completed,
        }
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            data=update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_reposense = self.client.get(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            format="json",
        )
        self.assertEqual(get_reposense.status_code, 200)
        self.assertEqual(get_reposense.data["id"], str(dispense_order.external_id))
        self.assertEqual(get_reposense.data["name"], update_data["name"])
        self.assertEqual(get_reposense.data["status"], update_data["status"])

    def test_update_dispense_order_as_pharmacist(self):
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Initial Dispense Order",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.pharmacist_role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "name": "Updated Dispense Order",
            "status": MedicationDispenseOrderStatusOptions.completed,
        }
        response = self.client.put(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            data=update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_reposense = self.client.get(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            format="json",
        )
        self.assertEqual(get_reposense.status_code, 200)
        self.assertEqual(get_reposense.data["id"], str(dispense_order.external_id))
        self.assertEqual(get_reposense.data["name"], update_data["name"])
        self.assertEqual(get_reposense.data["status"], update_data["status"])
