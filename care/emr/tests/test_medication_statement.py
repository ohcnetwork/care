from unittest.mock import patch

from django.urls import reverse
from model_bakery import baker

from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class TestMedicationStatementApi(CareAPITestBase):
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
            "medication-statement-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )
        self.valid_code = {
            "display": "Test Value",
            "system": "http://test_system.care/test",
            "code": "123",
        }
        # Mocking validate_valueset
        self.patcher = patch(
            "care.emr.resources.medication.statement.spec.validate_valueset",
            return_value=self.valid_code,
        )
        self.mock_validate_valueset = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _get_medication_statement_url(self, medication_statement_id):
        """Helper to get the detail URL for a specific medication statement."""
        return reverse(
            "medication-statement-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": medication_statement_id,
            },
        )

    def create_medication_statement(self, **kwargs):
        data = {
            "status": "active",
            "reason": "Test Reason",
            "medication": self.valid_code,
            "dosage_text": "1 mg",
            "encounter": self.encounter,
            "patient": self.patient,
            "information_source": "patient",
            "note": "Test Note",
        }
        data.update(kwargs)
        return baker.make("emr.MedicationStatement", **data)

    def get_medication_statement_data(self, **kwargs):
        data = {
            "status": "active",
            "reason": "Test Reason",
            "medication": self.valid_code,
            "dosage_text": "1 mg",
            "encounter": self.encounter.external_id,
            "information_source": "patient",
            "note": "Test Note",
        }
        data.update(kwargs)
        return data

    def test_list_medication_statement_with_permissions(self):
        """
        Users with `can_view_clinical_data` on a non-completed encounter
        can list medication statements (HTTP 200).
        """
        # Attach the needed role/permission
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_list_medication_statement_without_permissions(self):
        """
        Users without `can_view_clinical_data` => (HTTP 403).
        """
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_create_medication_statement_with_permission(self):
        """
        Users with `can_write_encounter_obj` permission can create medication statements (HTTP 200).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_medication_statement_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_medication_statement_without_permission(self):
        """
        Users without `can_write_encounter_obj` permission => (HTTP 403).
        """
        data = self.get_medication_statement_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_update_medication_statement_with_permission(self):
        """
        Users with `can_write_encounter_obj` and `can_view_clinical_data` permission can update medication statements (HTTP 200).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        obj = self.create_medication_statement()
        url = self._get_medication_statement_url(obj.external_id)
        data = self.get_medication_statement_data(status="intended")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self.assertEqual(obj.status, "intended")

    def test_update_medication_statement_without_permission(self):
        """
        Users without `can_write_encounter_obj` => HTTP 403
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        obj = self.create_medication_statement()
        url = self._get_medication_statement_url(obj.external_id)
        data = self.get_medication_statement_data()
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403)
