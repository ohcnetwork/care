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


class TestChronicConditionViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "chronic-condition-list",
            kwargs={"patient_external_id": self.patient.external_id},
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

    def _get_chronic_condition_url(self, chronic_condition_id):
        """Helper to get the detail URL for a specific chronic_condition."""
        return reverse(
            "chronic-condition-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": chronic_condition_id,
            },
        )

    def create_chronic_condition(self, encounter, patient, **kwargs):
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
            category=CategoryChoices.chronic_condition.value,
            clinical_status=clinical_status,
            verification_status=verification_status,
            severity=severity,
            **kwargs,
        )

    def generate_data_for_chronic_condition(self, encounter, **kwargs):
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
            "category": CategoryChoices.chronic_condition.value,
            "clinical_status": clinical_status,
            "verification_status": verification_status,
            "severity": severity,
            "code": code,
            **kwargs,
        }

    # LIST TESTS
    def test_list_chronic_condition_with_permissions(self):
        """
        Users with `can_view_clinical_data` on a non-completed encounter
        can list chronic_condition (HTTP 200).
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

    def test_list_chronic_condition_with_permissions_and_encounter_status_as_completed(
        self,
    ):
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

    def test_list_chronic_condition_without_permissions(self):
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

    def test_list_chronic_condition_for_single_encounter_with_permissions(self):
        """
        Users with `can_view_clinical_data` can list chronic_condition for that encounter (HTTP 200).
        """
        permissions = [PatientPermissions.can_view_clinical_data.name]
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

    def test_list_chronic_condition_for_single_encounter_with_permissions_and_encounter_status_completed(
        self,
    ):
        """
        Users with `can_view_clinical_data` on a completed encounter cannot list chronic_condition (HTTP 200).
        """
        permissions = [PatientPermissions.can_view_clinical_data.name]
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
        self.assertEqual(response.status_code, 403)

    def test_list_chronic_condition_for_single_encounter_without_permissions(self):
        """
        Users without `can_view_clinical_data` or `can_view_clinical_data` => (HTTP 403).
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
    def test_create_chronic_condition_without_permissions(self):
        """
        Users who lack `can_write_patient` get (HTTP 403) when creating.
        """
        # No permission attached
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )

        response = self.client.post(
            self.base_url, chronic_condition_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_chronic_condition_without_permissions_on_facility(self):
        """
        Tests that a user with `can_write_patient` permissions but belonging to a different
        organization receives (HTTP 403) when attempting to create a chronic_condition.
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            PatientPermissions.can_write_patient.name,
        ]
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
        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )

        response = self.client.post(
            self.base_url, chronic_condition_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_chronic_condition_with_organization_user_with_permissions(self):
        """
        Ensures that a user from a certain organization, who has both
        `can_write_patient` and `can_view_clinical_data`, can successfully
        view chronic_condition data (HTTP 200) and is able to edit chronic_condition
        and chronic_condition can change across encounters.
        """
        organization = self.create_organization(org_type="govt")
        patient = self.create_patient(geo_organization=organization)

        permissions = [
            PatientPermissions.can_write_patient.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(organization, self.user, role)

        # Verify the user can view chronic_condition data (HTTP 200)
        test_url = reverse(
            "chronic-condition-list",
            kwargs={"patient_external_id": patient.external_id},
        )
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)

        encounter = self.create_encounter(
            patient=patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )

        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )
        response = self.client.post(
            test_url, chronic_condition_data_dict, format="json"
        )

        self.assertEqual(response.status_code, 200)

    def test_create_chronic_condition_with_permissions(self):
        """
        Users with `can_write_patient` on a non-completed encounter => (HTTP 200).
        """
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )

        response = self.client.post(
            self.base_url, chronic_condition_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["severity"], chronic_condition_data_dict["severity"]
        )
        self.assertEqual(response.json()["code"], chronic_condition_data_dict["code"])

    def test_create_chronic_condition_with_permissions_and_encounter_status_completed(
        self,
    ):
        """
        Users with `can_write_patient` on a completed encounter => (HTTP 403).
        """
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )

        response = self.client.post(
            self.base_url, chronic_condition_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_chronic_condition_with_permissions_and_no_association_with_facility(
        self,
    ):
        """
        Test that users with `can_write_patient` permission, but who are not
        associated with the facility, receive an HTTP 403 (Forbidden) response
        when attempting to create a chronic_condition.
        """
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        organization = self.create_organization(org_type="govt")
        self.attach_role_organization_user(organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )

        response = self.client.post(
            self.base_url, chronic_condition_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_chronic_condition_with_permissions_with_mismatched_patient_id(self):
        """
        Users with `can_write_patient` on a encounter with different patient => (HTTP 403).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            PatientPermissions.can_write_patient.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )

        response = self.client.post(
            self.base_url, chronic_condition_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_chronic_condition_with_permissions_with_invalid_encounter_id(self):
        """
        Users with `can_write_patient` on a incomplete encounter => (HTTP 400).
        """
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=self.facility,
            organization=self.organization,
            status=None,
        )
        chronic_condition_data_dict = self.generate_data_for_chronic_condition(
            encounter
        )
        chronic_condition_data_dict["encounter"] = uuid.uuid4()

        response = self.client.post(
            self.base_url, chronic_condition_data_dict, format="json"
        )
        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "value_error")
        self.assertIn("Encounter not found", error["msg"])

    # RETRIEVE TESTS
    def test_retrieve_chronic_condition_with_permissions(self):
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
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(
            retrieve_response.data["id"], str(chronic_condition.external_id)
        )

    def test_retrieve_chronic_condition_for_single_encounter_with_permissions(self):
        """
        Users with `can_view_clinical_data` => (HTTP 200).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        retrieve_response = self.client.get(f"{url}?encounter={encounter.external_id}")
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(
            retrieve_response.data["id"], str(chronic_condition.external_id)
        )

    def test_retrieve_chronic_condition_for_single_encounter_without_permissions(self):
        """
        Lacking `can_view_clinical_data` => (HTTP 403).
        """
        # No relevant permission
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        retrieve_response = self.client.get(f"{url}?encounter={encounter.external_id}")
        self.assertEqual(retrieve_response.status_code, 403)

    def test_retrieve_chronic_condition_without_permissions(self):
        """
        Users who have only `can_write_patient` => (HTTP 403).
        """
        # No relevant permission
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 403)

    # UPDATE TESTS
    def test_update_chronic_condition_with_permissions(self):
        """
        Users with `can_write_encounter` + `can_write_patient` + `can_view_clinical_data`
        => (HTTP 200) when updating.
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            PatientPermissions.can_write_patient.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        chronic_condition_data_updated = model_to_dict(chronic_condition)
        chronic_condition_data_updated["encounter"] = encounter.external_id
        chronic_condition_data_updated["severity"] = "mild"
        chronic_condition_data_updated["code"] = self.valid_code

        response = self.client.put(url, chronic_condition_data_updated, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["severity"], "mild")

    def test_update_chronic_condition_for_single_encounter_with_permissions(self):
        """
        Users with `can_write_encounter` + `can_write_patient` + `can_view_clinical_data`
        => (HTTP 200).
        """
        permissions = [
            PatientPermissions.can_view_clinical_data.name,
            PatientPermissions.can_write_patient.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        chronic_condition_data_updated = model_to_dict(chronic_condition)
        chronic_condition_data_updated["encounter"] = encounter.external_id
        chronic_condition_data_updated["severity"] = "mild"
        chronic_condition_data_updated["code"] = self.valid_code

        update_response = self.client.put(
            f"{url}?encounter={encounter.external_id}",
            chronic_condition_data_updated,
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["severity"], "mild")

    def test_update_chronic_condition_for_single_encounter_without_permissions(self):
        """
        Lacking `can_view_clinical_data` => (HTTP 403).
        """
        # Only write permission
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        chronic_condition_data_updated = model_to_dict(chronic_condition)
        chronic_condition_data_updated["severity"] = "mild"

        update_response = self.client.put(
            f"{url}?encounter={encounter.external_id}",
            chronic_condition_data_updated,
            format="json",
        )
        self.assertEqual(update_response.status_code, 403)

    def test_update_chronic_condition_without_permissions(self):
        """
        Users with only `can_write_patient` but not `can_view_clinical_data`
        => (HTTP 403).
        """
        # Only write permission (same scenario as above but no read or view clinical)

        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        chronic_condition_data_updated = model_to_dict(chronic_condition)
        chronic_condition_data_updated["severity"] = "mild"

        update_response = self.client.put(
            url, chronic_condition_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 403)

    def test_update_chronic_condition_for_closed_encounter_with_permissions(self):
        """
        Encounter completed => (HTTP 403) on update,
        even if user has `can_write_patient` + `can_view_clinical_data`.
        """
        permissions = [
            PatientPermissions.can_write_patient.name,
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
        chronic_condition = self.create_chronic_condition(
            encounter=encounter, patient=self.patient
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        chronic_condition_data_updated = model_to_dict(chronic_condition)
        chronic_condition_data_updated["severity"] = "mild"

        update_response = self.client.put(
            url, chronic_condition_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 403)

    def test_update_chronic_condition_changes_encounter_id(self):
        """
        When a user with access to a new encounter
        updates a chronic_condition added by a different encounter,
        the encounter_id should be updated to the new encounter.
        """
        permissions = [
            PatientPermissions.can_write_patient.name,
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_write_encounter.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        temp_facility = self.create_facility(user=self.create_user())
        encounter = self.create_encounter(
            patient=self.patient,
            facility=temp_facility,
            organization=self.create_facility_organization(facility=temp_facility),
        )

        chronic_condition = self.create_chronic_condition(
            encounter=encounter,
            patient=self.patient,
            code=self.valid_code,
        )

        new_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        chronic_condition_data_updated = model_to_dict(chronic_condition)
        chronic_condition_data_updated["encounter"] = new_encounter.external_id
        chronic_condition_data_updated["clinical_status"] = "remission"

        update_response = self.client.put(
            url, chronic_condition_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["encounter"], str(new_encounter.external_id)
        )

    def test_update_chronic_condition_changes_encounter_id_without_permission(self):
        """
        When a user without access to a new encounter
        updates a chronic_condition added by a different encounter,
        the encounter_id should not be updated to the new encounter.
        """
        permissions = [
            PatientPermissions.can_write_patient.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        temp_facility = self.create_facility(user=self.create_user())
        encounter = self.create_encounter(
            patient=self.patient,
            facility=temp_facility,
            organization=self.create_facility_organization(facility=temp_facility),
        )

        chronic_condition = self.create_chronic_condition(
            encounter=encounter,
            patient=self.patient,
            code=self.valid_code,
        )

        new_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )

        url = self._get_chronic_condition_url(chronic_condition.external_id)
        chronic_condition_data_updated = model_to_dict(chronic_condition)
        chronic_condition_data_updated["encounter"] = new_encounter.external_id
        chronic_condition_data_updated["clinical_status"] = "remission"

        update_response = self.client.put(
            url, chronic_condition_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 403)
