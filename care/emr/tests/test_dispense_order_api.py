from django.urls import reverse
from model_bakery import baker

from care.emr.models import FacilityLocation, FacilityLocationOrganization
from care.emr.models.account import Account
from care.emr.models.charge_item import ChargeItem
from care.emr.models.inventory_item import InventoryItem
from care.emr.models.medication_dispense import DispenseOrder, MedicationDispense
from care.emr.models.medication_request import MedicationRequest
from care.emr.models.product import Product
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.location.spec import FacilityLocationModeChoices
from care.emr.resources.medication.dispense.dispense_order import (
    MedicationDispenseOrderStatusOptions,
)
from care.emr.resources.medication.dispense.spec import MedicationDispenseStatus
from care.emr.resources.medication.request.spec import MedicationRequestDispenseStatus
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
        location = baker.make(FacilityLocation, facility=facility, **kwargs)
        baker.make(
            FacilityLocationOrganization,
            location=location,
            organization=facility_organization,
        )
        return location

    def create_dispense_order(self, **kwargs):
        return baker.make(DispenseOrder, **kwargs)

    def create_medication_dispense_for_order(self, order, **overrides):
        account = baker.make(Account, facility=order.facility, patient=order.patient)
        charge_item = baker.make(
            ChargeItem,
            facility=order.facility,
            patient=order.patient,
            account=account,
            status=ChargeItemStatusOptions.billable.value,
            paid_invoice=None,
        )
        encounter = self.create_encounter(
            patient=order.patient,
            facility=order.facility,
            organization=self.facility_organization,
        )
        authorizing_request = overrides.pop(
            "authorizing_request",
            baker.make(
                MedicationRequest,
                patient=order.patient,
                encounter=encounter,
                dispense_status=MedicationRequestDispenseStatus.complete.value,
            ),
        )
        product = baker.make(Product, facility=order.facility)
        inventory_item = baker.make(
            InventoryItem, location=order.location, product=product
        )
        return baker.make(
            MedicationDispense,
            order=order,
            patient=order.patient,
            location=order.location,
            encounter=encounter,
            item=inventory_item,
            charge_item=charge_item,
            authorizing_request=authorizing_request,
            **overrides,
        )

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

    # Testcases for retrieving dispense order

    def test_retrieve_dispense_order_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Initial Dispense Order",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(dispense_order.external_id))
        self.assertEqual(response.data["name"], dispense_order.name)

    def test_retrieve_dispense_order_as_user_without_permission(self):
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Initial Dispense Order",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to read dispense order",
            response.data["detail"],
        )

    def test_retrieve_dispense_order_as_user_with_location_read_permission(self):
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
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(dispense_order.external_id))
        self.assertEqual(response.data["name"], dispense_order.name)

    def test_retrieve_dispense_order_as_pharmacist(self):
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
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(dispense_order.external_id))
        self.assertEqual(response.data["name"], dispense_order.name)

    # Testcases for listing dispense orders

    def test_list_dispense_orders_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order1 = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 1",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        dispense_order2 = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 2",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][1]["id"], str(dispense_order1.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["id"], str(dispense_order2.external_id)
        )

    def test_list_dispense_orders_as_user_without_permission(self):
        self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 1",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 2",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            {"location": self.location.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to read dispense order",
            response.data["detail"],
        )

    def test_list_dispense_orders_as_user_with_location_read_permission(self):
        dispense_order1 = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 1",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        dispense_order2 = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 2",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            {"location": self.location.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][1]["id"], str(dispense_order1.external_id)
        )
        self.assertEqual(
            response.data["results"][0]["id"], str(dispense_order2.external_id)
        )

    def test_list_dispense_orders_without_location(self):
        self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 1",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 2",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Location is required for non-pharmacists",
            response.data["errors"][0]["msg"],
        )

    def test_list_dispense_orders_with_status_filter(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 1",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        dispense_order2 = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 2",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            data={"status": MedicationDispenseOrderStatusOptions.completed},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(dispense_order2.external_id)
        )

    def test_list_dispense_orders_with_patient_filter(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Dispense Order 1",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        other_patient = self.create_patient()
        dispense_order2 = self.create_dispense_order(
            location=self.location,
            patient=other_patient,
            name="Dispense Order 2",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            data={"patient": str(other_patient.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(dispense_order2.external_id)
        )

    def test_list_dispense_orders_with_include_children_filter(self):
        parent_location = baker.make(
            FacilityLocation,
            facility=self.facility,
            name="Parent Location",
            mode=FacilityLocationModeChoices.kind.value,
        )
        baker.make(
            FacilityLocationOrganization,
            location=parent_location,
            organization=self.facility_organization,
        )

        child_location = baker.make(
            FacilityLocation,
            facility=self.facility,
            name="Child Location",
            parent=parent_location,
        )
        baker.make(
            FacilityLocationOrganization,
            location=child_location,
            organization=self.facility_organization,
        )

        order_at_parent = self.create_dispense_order(
            location=parent_location,
            patient=self.patient,
            name="Order at Parent",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        order_at_child = self.create_dispense_order(
            location=child_location,
            patient=self.patient,
            name="Order at Child",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )

        self.attach_role_facility_organization_user(
            user=self.user,
            role=self.role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            {"location": str(parent_location.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(order_at_parent.external_id)
        )

        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            {
                "location": str(parent_location.external_id),
                "include_children": "false",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            {"location": str(parent_location.external_id), "include_children": "true"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        order_ids = [result["id"] for result in response.data["results"]]
        self.assertIn(str(order_at_parent.external_id), order_ids)
        self.assertIn(str(order_at_child.external_id), order_ids)

        response = self.client.get(
            self.generate_base_url(self.facility.external_id),
            {"location": str(parent_location.external_id), "include_children": "TRUE"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    # Testcases for status transitions / cancellation of dispense order

    def _put_status(self, dispense_order, status):
        return self.client.put(
            self.get_detail_url(self.facility.external_id, dispense_order.external_id),
            data={"name": dispense_order.name, "status": status},
            format="json",
        )

    def test_update_dispense_order_completed_to_abandoned_allowed(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.abandoned
        )
        self.assertEqual(response.status_code, 200)
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.abandoned.value,
        )

    def test_update_dispense_order_completed_to_entered_in_error_allowed(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.entered_in_error
        )
        self.assertEqual(response.status_code, 200)
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.entered_in_error.value,
        )

    def test_update_dispense_order_completed_to_draft_rejected(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.draft
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Dispense order can only be cancelled",
            response.data["errors"][0]["msg"],
        )
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.completed.value,
        )

    def test_update_dispense_order_completed_to_in_progress_rejected(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.in_progress
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Dispense order can only be cancelled",
            response.data["errors"][0]["msg"],
        )

    def test_update_dispense_order_abandoned_cannot_change(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Abandoned Order",
            status=MedicationDispenseOrderStatusOptions.abandoned,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.completed
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "already abandoned or entered in error",
            response.data["errors"][0]["msg"],
        )
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.abandoned.value,
        )

    def test_update_dispense_order_entered_in_error_cannot_change(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Errored Order",
            status=MedicationDispenseOrderStatusOptions.entered_in_error,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.draft
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "already abandoned or entered in error",
            response.data["errors"][0]["msg"],
        )

    def test_update_dispense_order_same_status_no_op(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.completed
        )
        self.assertEqual(response.status_code, 200)
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.completed.value,
        )

    def test_update_dispense_order_draft_to_completed_allowed(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Draft Order",
            status=MedicationDispenseOrderStatusOptions.draft,
            facility=self.facility,
        )
        # Attach a related dispense to confirm cancel logic is NOT triggered
        # when transitioning out of a non-completed state.
        related = self.create_medication_dispense_for_order(dispense_order)
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.completed
        )
        self.assertEqual(response.status_code, 200)
        related.refresh_from_db()
        self.assertIsNotNone(related.authorizing_request_id)
        related.charge_item.refresh_from_db()
        self.assertEqual(
            related.charge_item.status, ChargeItemStatusOptions.billable.value
        )

    def _assert_cancelled_side_effects(self, dispenses, expected_dispense_status):
        for dispense in dispenses:
            original_request_id = dispense.authorizing_request_id
            dispense.refresh_from_db()
            self.assertIsNone(dispense.authorizing_request_id)
            self.assertEqual(dispense.status, expected_dispense_status)
            dispense.charge_item.refresh_from_db()
            self.assertEqual(
                dispense.charge_item.status,
                ChargeItemStatusOptions.aborted.value,
            )
            request = MedicationRequest.objects.get(id=original_request_id)
            self.assertEqual(
                request.dispense_status,
                MedicationRequestDispenseStatus.incomplete.value,
            )

    def test_cancel_completed_dispense_order_updates_related_records(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        dispenses = [
            self.create_medication_dispense_for_order(dispense_order),
            self.create_medication_dispense_for_order(dispense_order),
        ]
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.abandoned
        )
        self.assertEqual(response.status_code, 200)
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.abandoned.value,
        )
        self._assert_cancelled_side_effects(
            dispenses, MedicationDispenseStatus.cancelled.value
        )

    def test_cancel_completed_dispense_order_via_entered_in_error(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        dispenses = [self.create_medication_dispense_for_order(dispense_order)]
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.entered_in_error
        )
        self.assertEqual(response.status_code, 200)
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.entered_in_error.value,
        )
        self._assert_cancelled_side_effects(
            dispenses, MedicationDispenseStatus.entered_in_error.value
        )

    def test_cancel_completed_dispense_order_with_no_related_dispenses(self):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.abandoned
        )
        self.assertEqual(response.status_code, 200)
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.abandoned.value,
        )

    def test_cancel_completed_dispense_order_with_dispense_missing_authorizing_request(
        self,
    ):
        self.client.force_authenticate(user=self.superuser)
        dispense_order = self.create_dispense_order(
            location=self.location,
            patient=self.patient,
            name="Completed Order",
            status=MedicationDispenseOrderStatusOptions.completed,
            facility=self.facility,
        )
        dispense_with_request = self.create_medication_dispense_for_order(
            dispense_order
        )
        dispense_without_request = self.create_medication_dispense_for_order(
            dispense_order, authorizing_request=None
        )
        response = self._put_status(
            dispense_order, MedicationDispenseOrderStatusOptions.abandoned
        )
        self.assertEqual(response.status_code, 200)
        dispense_order.refresh_from_db()
        self.assertEqual(
            dispense_order.status,
            MedicationDispenseOrderStatusOptions.abandoned.value,
        )
        # Dispense without an authorizing_request should still have its charge_item
        # cancelled, status set to cancelled, and remain without an authorizing_request.
        dispense_without_request.refresh_from_db()
        self.assertIsNone(dispense_without_request.authorizing_request_id)
        self.assertEqual(
            dispense_without_request.status,
            MedicationDispenseStatus.cancelled.value,
        )
        dispense_without_request.charge_item.refresh_from_db()
        self.assertEqual(
            dispense_without_request.charge_item.status,
            ChargeItemStatusOptions.aborted.value,
        )
        # Dispense with an authorizing_request should have full cancel side effects.
        self._assert_cancelled_side_effects(
            [dispense_with_request], MedicationDispenseStatus.cancelled.value
        )
