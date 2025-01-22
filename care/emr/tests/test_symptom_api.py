import uuid
from secrets import choice
from unittest.mock import patch

from django.forms import model_to_dict
from django.urls import reverse
from model_bakery import baker

from care.emr.models import Condition
from care.emr.resources.condition.spec import (
    CategoryChoices,
    ClinicalStatusChoices,
    SeverityChoices,
    VerificationStatusChoices,
)
from care.emr.resources.resource_request.spec import StatusChoices
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class TestSymptomViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "symptom-list", kwargs={"patient_external_id": self.patient.external_id}
        )
        self.valid_code = {
            "display": "Test Value",
            "system": "http://test_system.care/test",
            "code": "123",
        }
        # Mocking validate_valueset
        self.patcher = patch(
            "care.emr.resources.condition.spec.validate_valueset",
            return_value=self.valid_code,
        )
        self.mock_validate_valueset = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _get_symptom_url(self, symptom_id):
        """Helper to get the detail URL for a specific symptom."""
        return reverse(
            "symptom-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": symptom_id,
            },
        )

    def create_symptom(self, encounter, patient, **kwargs):
        clinical_status = kwargs.pop(
            "clinical_status", choice(list(ClinicalStatusChoices)).value
        )
        verification_status = kwargs.pop(
            "verification_status", choice(list(VerificationStatusChoices)).value
        )
        severity = kwargs.pop("severity", choice(list(SeverityChoices)).value)

        return baker.make(
            Condition,
            encounter=encounter,
            patient=patient,
            category=CategoryChoices.problem_list_item.value,
            clinical_status=clinical_status,
            verification_status=verification_status,
            severity=severity,
            **kwargs,
        )

    def generate_data_for_symptom(self, encounter, **kwargs):
        clinical_status = kwargs.pop(
            "clinical_status", choice(list(ClinicalStatusChoices)).value
        )
        verification_status = kwargs.pop(
            "verification_status", choice(list(VerificationStatusChoices)).value
        )
        severity = kwargs.pop("severity", choice(list(SeverityChoices)).value)
        code = self.valid_code
        return {
            "encounter": encounter.external_id,
            "category": CategoryChoices.problem_list_item.value,
            "clinical_status": clinical_status,
            "verification_status": verification_status,
            "severity": severity,
            "code": code,
            **kwargs,
        }

    # LIST TESTS
    def test_list_symptoms_with_permissions(self):
        """
        Users with `can_view_clinical_data` on a non-completed encounter
        can list symptoms (HTTP 200).
        """
        # Attach the needed role/permission
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Create an active encounter
        self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_list_symptoms_with_permissions_and_encounter_status_as_completed(self):
        """
        Users with `can_view_clinical_data` but a completed encounter => (HTTP 403).
        """
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_symptoms_without_permissions(self):
        """
        Users without `can_view_clinical_data` => (HTTP 403).
        """
        # No permission attached
        self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_symptoms_for_single_encounter_with_permissions(self):
        """
        Users with `can_read_encounter` can list symptoms for that encounter (HTTP 200).
        """
        permissions = [EncounterPermissions.can_read_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )

        url = f"{self.base_url}?encounter={encounter.external_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list_symptoms_for_single_encounter_with_permissions_and_encounter_status_completed(
        self,
    ):
        """
        Users with `can_read_encounter` on a completed encounter can still list symptoms (HTTP 200).
        """
        permissions = [EncounterPermissions.can_read_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        url = f"{self.base_url}?encounter={encounter.external_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list_symptoms_for_single_encounter_without_permissions(self):
        """
        Users without `can_read_encounter` or `can_view_clinical_data` => (HTTP 403).
        """
        # No relevant permission
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        url = f"{self.base_url}?encounter={encounter.external_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    # CREATE TESTS
    def test_create_symptom_without_permissions(self):
        """
        Users who lack `can_write_encounter` get (HTTP 403) when creating.
        """
        # No permission attached
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        symptom_data_dict = self.generate_data_for_symptom(encounter)

        response = self.client.post(self.base_url, symptom_data_dict, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_symptom_without_permissions_on_facility(self):
        """
        Tests that a user with `can_write_encounter` permissions but belonging to a different
        organization receives (HTTP 403) when attempting to create a symptom.
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        external_user = self.create_user()
        external_facility = self.create_facility(user=external_user)
        external_organization = self.create_facility_organization(
            facility=external_facility
        )
        self.attach_role_facility_organization_user(
            external_organization, self.user, role
        )

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        symptom_data_dict = self.generate_data_for_symptom(encounter)

        response = self.client.post(self.base_url, symptom_data_dict, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_symptom_with_organisation_user_with_permissions(self):
        """
        Ensures that a user from a certain organization, who has both
        `can_write_encounter` and `can_view_clinical_data`, can successfully
        view symptom data (HTTP 200) but still receives (HTTP 403) when attempting
        to create a symptom for an encounter.
        """
        organization = self.create_organization(org_type="govt")
        patient = self.create_patient(geo_organization=organization)

        permissions = [
            EncounterPermissions.can_write_encounter.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(organization, self.user, role)

        # Verify the user can view symptom data (HTTP 200)
        test_url = reverse(
            "symptom-list", kwargs={"patient_external_id": patient.external_id}
        )
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

        encounter = self.create_encounter(
            patient=patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )

        symptom_data_dict = self.generate_data_for_symptom(encounter)
        response = self.client.post(test_url, symptom_data_dict, format="json")

        # User gets 403 because the encounter belongs to a different organization
        self.assertEqual(response.status_code, 403)

    def test_create_symptom_with_permissions(self):
        """
        Users with `can_write_encounter` on a non-completed encounter => (HTTP 200).
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        symptom_data_dict = self.generate_data_for_symptom(encounter)

        response = self.client.post(self.base_url, symptom_data_dict, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["severity"], symptom_data_dict["severity"])
        self.assertEqual(response.json()["code"], symptom_data_dict["code"])

    def test_create_symptom_with_permissions_and_encounter_status_completed(self):
        """
        Users with `can_write_encounter` on a completed encounter => (HTTP 403).
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        symptom_data_dict = self.generate_data_for_symptom(encounter)

        response = self.client.post(self.base_url, symptom_data_dict, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_symptom_with_permissions_and_no_association_with_facility(self):
        """
        Test that users with `can_write_encounter` permission, but who are not
        associated with the facility, receive an HTTP 403 (Forbidden) response
        when attempting to create a symptom.
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        organization = self.create_organization(org_type="govt")
        self.attach_role_organization_user(organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        symptom_data_dict = self.generate_data_for_symptom(encounter)

        response = self.client.post(self.base_url, symptom_data_dict, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_symptoms_with_permissions_with_mismatched_patient_id(self):
        """
        Users with `can_write_encounter` on a encounter with different patient => (HTTP 400).
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        symptom_data_dict = self.generate_data_for_symptom(encounter)

        response = self.client.post(self.base_url, symptom_data_dict, format="json")
        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn(
            "Patient external ID mismatch with encounter's patient", error["msg"]
        )

    def test_create_symptom_with_permissions_with_invalid_encounter_id(self):
        """
        Users with `can_write_encounter` on a incomplete encounter => (HTTP 400).
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        symptom_data_dict = self.generate_data_for_symptom(encounter)
        symptom_data_dict["encounter"] = uuid.uuid4()

        response = self.client.post(self.base_url, symptom_data_dict, format="json")
        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "value_error")
        self.assertIn("Encounter not found", error["msg"])

    # RETRIEVE TESTS
    def test_retrieve_symptom_with_permissions(self):
        """
        Users with `can_view_clinical_data` => (HTTP 200).
        """
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(retrieve_response.data["id"], str(symptom.external_id))

    def test_retrieve_symptom_for_single_encounter_with_permissions(self):
        """
        Users with `can_read_encounter` => (HTTP 200).
        """
        permissions = [EncounterPermissions.can_read_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        retrieve_response = self.client.get(f"{url}?encounter={encounter.external_id}")
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(retrieve_response.data["id"], str(symptom.external_id))

    def test_retrieve_symptom_for_single_encounter_without_permissions(self):
        """
        Lacking `can_read_encounter` => (HTTP 403).
        """
        # No relevant permission
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        retrieve_response = self.client.get(f"{url}?encounter={encounter.external_id}")
        self.assertEqual(retrieve_response.status_code, 403)

    def test_retrieve_symptom_without_permissions(self):
        """
        Users who have only `can_write_encounter` => (HTTP 403).
        """
        # No relevant permission
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 403)

    # UPDATE TESTS
    def test_update_symptom_with_permissions(self):
        """
        Users with `can_write_encounter` + `can_view_clinical_data`
        => (HTTP 200) when updating.
        """
        permissions = [
            EncounterPermissions.can_write_encounter.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        symptom_data_updated = model_to_dict(symptom)
        symptom_data_updated["severity"] = "mild"
        symptom_data_updated["code"] = self.valid_code

        response = self.client.put(url, symptom_data_updated, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["severity"], "mild")

    def test_update_symptom_for_single_encounter_with_permissions(self):
        """
        Users with `can_write_encounter` + `can_read_encounter`
        => (HTTP 200).
        """
        permissions = [
            EncounterPermissions.can_write_encounter.name,
            EncounterPermissions.can_read_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        symptom_data_updated = model_to_dict(symptom)
        symptom_data_updated["severity"] = "mild"
        symptom_data_updated["code"] = self.valid_code

        update_response = self.client.put(
            f"{url}?encounter={encounter.external_id}",
            symptom_data_updated,
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["severity"], "mild")

    def test_update_symptom_for_single_encounter_without_permissions(self):
        """
        Lacking `can_read_encounter` => (HTTP 403).
        """
        # Only write permission
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        symptom_data_updated = model_to_dict(symptom)
        symptom_data_updated["severity"] = "mild"

        update_response = self.client.put(
            f"{url}?encounter={encounter.external_id}",
            symptom_data_updated,
            format="json",
        )
        self.assertEqual(update_response.status_code, 403)

    def test_update_symptom_without_permissions(self):
        """
        Users with only `can_write_encounter` but not `can_view_clinical_data`
        => (HTTP 403).
        """
        # Only write permission (same scenario as above but no read or view clinical)

        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        symptom_data_updated = model_to_dict(symptom)
        symptom_data_updated["severity"] = "mild"

        update_response = self.client.put(url, symptom_data_updated, format="json")
        self.assertEqual(update_response.status_code, 403)

    def test_update_symptom_for_closed_encounter_with_permissions(self):
        """
        Encounter completed => (HTTP 403) on update,
        even if user has `can_write_encounter` + `can_view_clinical_data`.
        """
        permissions = [
            EncounterPermissions.can_write_encounter.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        symptom_data_updated = model_to_dict(symptom)
        symptom_data_updated["severity"] = "mild"

        update_response = self.client.put(url, symptom_data_updated, format="json")
        self.assertEqual(update_response.status_code, 403)

    # DELETE TESTS
    def test_delete_symptom_with_permission(self):
        """
        Users with `can_write_encounter` + `can_view_clinical_data` => (HTTP 204).
        """
        permissions = [
            EncounterPermissions.can_write_encounter.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        delete_response = self.client.delete(url, {}, format="json")
        self.assertEqual(delete_response.status_code, 204)

    def test_delete_symptom_for_single_encounter_with_permission(self):
        """
        Users with `can_write_encounter` + `can_read_encounter` => (HTTP 204).
        """
        permissions = [
            EncounterPermissions.can_write_encounter.name,
            EncounterPermissions.can_read_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = f"{self._get_symptom_url(symptom.external_id)}?encounter={encounter.external_id}"
        delete_response = self.client.delete(url, {}, format="json")
        self.assertEqual(delete_response.status_code, 204)

    def test_delete_symptom_for_single_encounter_without_permission(self):
        """
        Lacking `can_read_encounter` => (HTTP 403) on delete.
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = f"{self._get_symptom_url(symptom.external_id)}?encounter={encounter.external_id}"
        delete_response = self.client.delete(url, {}, format="json")
        self.assertEqual(delete_response.status_code, 403)

    def test_delete_symptom_without_permission(self):
        """
        Users who only have `can_write_encounter` but not `can_view_clinical_data`
        => (HTTP 403) on delete.
        """
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        symptom = self.create_symptom(encounter=encounter, patient=self.patient)

        url = self._get_symptom_url(symptom.external_id)
        delete_response = self.client.delete(url, {}, format="json")
        self.assertEqual(delete_response.status_code, 403)
