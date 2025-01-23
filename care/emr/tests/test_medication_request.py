from datetime import UTC, datetime
from unittest.mock import patch

from django.urls import reverse
from model_bakery import baker

from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class TestMedicationRequestApi(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "medication-request-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )
        self.valid_code = {
            "display": "Test Value",
            "system": "http://test_system.care/test",
            "code": "123",
        }
        # Mocking validate_valueset
        self.patcher = patch(
            "care.emr.resources.medication.request.spec.validate_valueset",
            return_value=self.valid_code,
        )
        self.mock_validate_valueset = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _get_medication_request_url(self, medication_request_id):
        """Helper to get the detail URL for a specific medication request."""
        return reverse(
            "medication-request-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": medication_request_id,
            },
        )

    def create_medication_request(self, **kwargs):
        data = {
            "patient": self.patient,
            "encounter": self.encounter,
            "status": "active",
            "intent": "order",
            "category": "inpatient",
            "priority": "routine",
            "do_not_perform": False,
            "medication": self.valid_code,
            "dosage_instruction": [],
            "authored_on": datetime.now(UTC),
        }
        data.update(kwargs)
        return baker.make("emr.MedicationRequest", **data)

    def get_medication_request_data(self, **kwargs):
        data = {
            "status": "active",
            "intent": "order",
            "category": "inpatient",
            "priority": "routine",
            "do_not_perform": False,
            "medication": self.valid_code,
            "dosage_instruction": [],
            "authored_on": datetime.now(UTC),
            "encounter": self.encounter.external_id,
        }
        data.update(kwargs)
        return data

    def test_list_medication_request_with_permissions(self):
        """
        Users with `can_view_clinical_data` on a non-completed encounter
        can list medication requests (HTTP 200).
        """
        # Attach the needed role/permission
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_list_medication_request_without_permissions(self):
        """
        Users without `can_view_clinical_data` => (HTTP 403).
        """
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_create_medication_request_with_permission(self):
        """
        Users with `can_write_encounter_obj` permission can create medication requests (HTTP 200).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_medication_request_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_medication_request_with_permission_for_requester(self):
        """
        Users with `can_write_encounter_obj` permission can create medication requests as long as requester has the same permissions (HTTP 200).
        """
        requester = self.create_user()

        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.attach_role_facility_organization_user(self.organization, requester, role)

        data = self.get_medication_request_data(requester=requester.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_medication_request_without_permission_for_requester(self):
        """
        Requester without `can_write_encounter_obj` permission cannot create medication requests (HTTP 200).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        requester = self.create_user()
        requester_role = self.create_role_with_permissions([])
        self.attach_role_facility_organization_user(
            self.organization, requester, requester_role
        )

        data = self.get_medication_request_data(requester=requester.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            response,
            "Requester does not have permission to update encounter",
            status_code=403,
        )

    def test_create_medication_request_without_permission(self):
        """
        Users without `can_write_encounter_obj` permission => (HTTP 403).
        """
        data = self.get_medication_request_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_update_medication_request_with_permission(self):
        """
        Users with `can_write_encounter_obj` and `can_view_clinical_data` permission can update medication requests (HTTP 200).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        obj = self.create_medication_request()
        url = self._get_medication_request_url(obj.external_id)
        data = self.get_medication_request_data()
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_update_medication_request_without_permission(self):
        """
        Users without `can_write_encounter_obj` => HTTP 403
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        obj = self.create_medication_request()
        url = self._get_medication_request_url(obj.external_id)
        data = self.get_medication_request_data()
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_update_medication_request_requester(self):
        """
        Requester cannot be updated.
        """
        requester_initial, requester_updated = self.create_user(), self.create_user()

        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.attach_role_facility_organization_user(
            self.organization, requester_initial, role
        )
        self.attach_role_facility_organization_user(
            self.organization, requester_updated, role
        )

        obj = self.create_medication_request(requester=requester_initial)
        url = self._get_medication_request_url(obj.external_id)
        data = self.get_medication_request_data(requester=requester_updated.external_id)
        self.client.put(url, data, format="json")

        obj.refresh_from_db()
        self.assertEqual(obj.requester, requester_initial)
