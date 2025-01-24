import uuid
from secrets import choice
from unittest.mock import patch

from django.forms import model_to_dict
from django.urls import reverse
from model_bakery import baker

from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.resources.allergy_intolerance.spec import (
    CategoryChoices,
    ClinicalStatusChoices,
    CriticalityChoices,
    VerificationStatusChoices,
)
from care.emr.resources.resource_request.spec import StatusChoices
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class TestAllergyIntoleranceViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "allergy-intolerance-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )
        self.valid_code = {
            "display": "Test Value",
            "system": "http://test_system.care/test",
            "code": "123",
        }
        # Mocking validate_valueset
        self.patcher = patch(
            "care.emr.resources.allergy_intolerance.spec.validate_valueset",
            return_value=self.valid_code,
        )
        self.mock_validate_valueset = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _get_allergy_intolerance_url(self, allergy_intolerance_id):
        """Helper to get the detail URL for a specific allergy_intolerance."""
        return reverse(
            "allergy-intolerance-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": allergy_intolerance_id,
            },
        )

    def create_allergy_intolerance(self, encounter, patient, **kwargs):
        clinical_status = kwargs.pop(
            "clinical_status", choice(list(ClinicalStatusChoices)).value
        )
        verification_status = kwargs.pop(
            "verification_status", choice(list(VerificationStatusChoices)).value
        )
        category = kwargs.pop("category", choice(list(CategoryChoices)).value)
        criticality = kwargs.pop("criticality", choice(list(CriticalityChoices)).value)

        return baker.make(
            AllergyIntolerance,
            encounter=encounter,
            patient=patient,
            category=category,
            clinical_status=clinical_status,
            verification_status=verification_status,
            criticality=criticality,
            **kwargs,
        )

    def generate_data_for_allergy_intolerance(self, encounter, **kwargs):
        clinical_status = kwargs.pop(
            "clinical_status", choice(list(ClinicalStatusChoices)).value
        )
        verification_status = kwargs.pop(
            "verification_status", choice(list(VerificationStatusChoices)).value
        )
        category = kwargs.pop("category", choice(list(CategoryChoices)).value)
        criticality = kwargs.pop("criticality", choice(list(CriticalityChoices)).value)
        code = self.valid_code
        return {
            "encounter": encounter.external_id,
            "category": category,
            "clinical_status": clinical_status,
            "verification_status": verification_status,
            "criticality": criticality,
            "code": code,
            **kwargs,
        }

    # LIST TESTS
    def test_list_allergy_intolerance_with_permissions(self):
        """
        Users with `can_view_clinical_data` on a non-completed encounter
        can list allergy_intolerance (HTTP 200).
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

    def test_list_allergy_intolerance_with_permissions_and_encounter_status_as_completed(
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

    def test_list_allergy_intolerance_without_permissions(self):
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

    def test_list_allergy_intolerance_for_single_encounter_with_permissions(self):
        """
        Users with `can_view_clinical_data` can list allergy_intolerance for that encounter (HTTP 200).
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

    def test_list_allergy_intolerance_for_single_encounter_with_permissions_and_encounter_status_completed(
        self,
    ):
        """
        Users with `can_view_clinical_data` on a completed encounter cannot list allergy_intolerance (HTTP 200).
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

    def test_list_allergy_intolerance_for_single_encounter_without_permissions(self):
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
    def test_create_allergy_intolerance_without_permissions(self):
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
        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )

        response = self.client.post(
            self.base_url, allergy_intolerance_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_allergy_intolerance_without_permissions_on_facility(self):
        """
        Tests that a user with `can_write_patient` permissions but belonging to a different
        organization receives (HTTP 403) when attempting to create a allergy_intolerance.
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
        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )

        response = self.client.post(
            self.base_url, allergy_intolerance_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_allergy_intolerance_with_organization_user_with_permissions(self):
        """
        Ensures that a user from a certain organization, who has both
        `can_write_patient` and `can_view_clinical_data`, can successfully
        view allergy_intolerance data (HTTP 200) and is able to edit allergy_intolerance
        and allergy_intolerance can change across encounters.
        """
        organization = self.create_organization(org_type="govt")
        patient = self.create_patient(geo_organization=organization)

        permissions = [
            PatientPermissions.can_write_patient.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(organization, self.user, role)

        # Verify the user can view allergy_intolerance data (HTTP 200)
        test_url = reverse(
            "allergy-intolerance-list",
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

        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )
        response = self.client.post(
            test_url, allergy_intolerance_data_dict, format="json"
        )

        self.assertEqual(response.status_code, 200)

    def test_create_allergy_intolerance_with_permissions(self):
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
        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )

        response = self.client.post(
            self.base_url, allergy_intolerance_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["criticality"], allergy_intolerance_data_dict["criticality"]
        )
        self.assertEqual(response.json()["code"], allergy_intolerance_data_dict["code"])

    def test_create_allergy_intolerance_with_permissions_and_encounter_status_completed(
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
        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )

        response = self.client.post(
            self.base_url, allergy_intolerance_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_allergy_intolerance_with_permissions_and_no_association_with_facility(
        self,
    ):
        """
        Test that users with `can_write_patient` permission, but who are not
        associated with the facility, receive an HTTP 403 (Forbidden) response
        when attempting to create a allergy_intolerance.
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
        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )

        response = self.client.post(
            self.base_url, allergy_intolerance_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_allergy_intolerance_with_permissions_with_mismatched_patient_id(
        self,
    ):
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
        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )

        response = self.client.post(
            self.base_url, allergy_intolerance_data_dict, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_create_allergy_intolerance_with_permissions_with_invalid_encounter_id(
        self,
    ):
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
        allergy_intolerance_data_dict = self.generate_data_for_allergy_intolerance(
            encounter
        )
        allergy_intolerance_data_dict["encounter"] = uuid.uuid4()

        response = self.client.post(
            self.base_url, allergy_intolerance_data_dict, format="json"
        )
        response_data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "value_error")
        self.assertIn("Encounter not found", error["msg"])

    # RETRIEVE TESTS
    def test_retrieve_allergy_intolerance_with_permissions(self):
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
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(
            retrieve_response.data["id"], str(allergy_intolerance.external_id)
        )

    def test_retrieve_allergy_intolerance_for_single_encounter_with_permissions(self):
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
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        retrieve_response = self.client.get(f"{url}?encounter={encounter.external_id}")
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(
            retrieve_response.data["id"], str(allergy_intolerance.external_id)
        )

    def test_retrieve_allergy_intolerance_for_single_encounter_without_permissions(
        self,
    ):
        """
        Lacking `can_view_clinical_data` => (HTTP 403).
        """
        # No relevant permission
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        retrieve_response = self.client.get(f"{url}?encounter={encounter.external_id}")
        self.assertEqual(retrieve_response.status_code, 403)

    def test_retrieve_allergy_intolerance_without_permissions(self):
        """
        Users who have only `can_write_patient` => (HTTP 403).
        """
        # No relevant permission
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        retrieve_response = self.client.get(url)
        self.assertEqual(retrieve_response.status_code, 403)

    # UPDATE TESTS
    def test_update_allergy_intolerance_with_permissions(self):
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
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        allergy_intolerance_data_updated = model_to_dict(allergy_intolerance)
        allergy_intolerance_data_updated["encounter"] = encounter.external_id
        allergy_intolerance_data_updated["criticality"] = "high"
        allergy_intolerance_data_updated["code"] = self.valid_code

        response = self.client.put(url, allergy_intolerance_data_updated, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["criticality"], "high")

    def test_update_allergy_intolerance_for_single_encounter_with_permissions(self):
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
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        allergy_intolerance_data_updated = model_to_dict(allergy_intolerance)
        allergy_intolerance_data_updated["encounter"] = encounter.external_id
        allergy_intolerance_data_updated["criticality"] = "high"
        allergy_intolerance_data_updated["code"] = self.valid_code

        update_response = self.client.put(
            f"{url}?encounter={encounter.external_id}",
            allergy_intolerance_data_updated,
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["criticality"], "high")

    def test_update_allergy_intolerance_for_single_encounter_without_permissions(self):
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
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        allergy_intolerance_data_updated = model_to_dict(allergy_intolerance)
        allergy_intolerance_data_updated["criticality"] = "high"

        update_response = self.client.put(
            f"{url}?encounter={encounter.external_id}",
            allergy_intolerance_data_updated,
            format="json",
        )
        self.assertEqual(update_response.status_code, 403)

    def test_update_allergy_intolerance_without_permissions(self):
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
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        allergy_intolerance_data_updated = model_to_dict(allergy_intolerance)
        allergy_intolerance_data_updated["criticality"] = "high"

        update_response = self.client.put(
            url, allergy_intolerance_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 403)

    def test_update_allergy_intolerance_for_closed_encounter_with_permissions(self):
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
        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter, patient=self.patient
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        allergy_intolerance_data_updated = model_to_dict(allergy_intolerance)
        allergy_intolerance_data_updated["criticality"] = "high"

        update_response = self.client.put(
            url, allergy_intolerance_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 403)

    def test_update_allergy_intolerance_changes_encounter_id(self):
        """
        When a user with access to a new encounter
        updates a allergy_intolerance added by a different encounter,
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

        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter,
            patient=self.patient,
            code=self.valid_code,
        )

        new_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        allergy_intolerance_data_updated = model_to_dict(allergy_intolerance)
        allergy_intolerance_data_updated["encounter"] = new_encounter.external_id
        allergy_intolerance_data_updated["clinical_status"] = "inactive"

        update_response = self.client.put(
            url, allergy_intolerance_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["encounter"], str(new_encounter.external_id)
        )

    def test_update_allergy_intolerance_changes_encounter_id_without_permission(self):
        """
        When a user without access to a new encounter
        updates a allergy_intolerance added by a different encounter,
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

        allergy_intolerance = self.create_allergy_intolerance(
            encounter=encounter,
            patient=self.patient,
            code=self.valid_code,
        )

        new_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )

        url = self._get_allergy_intolerance_url(allergy_intolerance.external_id)
        allergy_intolerance_data_updated = model_to_dict(allergy_intolerance)
        allergy_intolerance_data_updated["encounter"] = new_encounter.external_id
        allergy_intolerance_data_updated["clinical_status"] = "inactive"

        update_response = self.client.put(
            url, allergy_intolerance_data_updated, format="json"
        )
        self.assertEqual(update_response.status_code, 403)
