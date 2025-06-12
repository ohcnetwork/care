import uuid
from secrets import choice
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework import status

from care.emr.models.location import FacilityLocation, FacilityLocationEncounter
from care.emr.resources.encounter.constants import (
    ClassChoices,
    EncounterPriorityChoices,
)
from care.emr.resources.encounter.spec import StatusChoices
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class EncounterAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            status_history={"history": []},
            encounter_class_history={"history": []},
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("encounter-list")
        self.encounter_data = {
            "patient": str(self.patient.external_id),
            "facility": str(self.facility.external_id),
            "status": StatusChoices.in_progress.value,
            "encounter_class": choice(list(ClassChoices)).value,
            "priority": choice(list(EncounterPriorityChoices)).value,
            "discharge_summary_advice": "",
            "external_identifier": "12345",
        }

    def _get_detail_url(self, facility_external_id, patient_external_id):
        url = reverse(
            "encounter-detail", kwargs={"external_id": self.encounter.external_id}
        )
        url += f"?facility={facility_external_id}&patient={patient_external_id}"
        return url

    def get_list_view_permission(self):
        permissions = [
            EncounterPermissions.can_list_encounter.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )

    #  TESTS FOR LIST FILTERS

    def test_filter_by_facility(self):
        self.get_list_view_permission()
        response = self.client.get(self.url, {"facility": self.facility.external_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_status(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {"status": self.encounter.status, "facility": self.facility.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_patient_name(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url, {"name": self.patient.name, "facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_patient_phone(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "phone_number": self.patient.phone_number,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_location(self):
        location = baker.make(
            FacilityLocation,
            facility=self.facility,
            status="ACTIVE",
            operational_status="ACTIVE",
            name="Test Location",
            description="Test Description",
            mode="INSTANCE",
            form="AREA",
        )

        baker.make(
            FacilityLocationEncounter,
            location=location,
            encounter=self.encounter,
            status="ACTIVE",
            start_datetime=timezone.now(),
        )
        location.current_encounter = self.encounter
        location.save()
        self.encounter.current_location = location
        self.encounter.save()

        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "location": str(location.external_id),
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filters_by_live(self):
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            status="completed",
        )
        self.get_list_view_permission()
        response = self.client.get(
            self.url, {"live": True, "facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(encounter.external_id))

        response = self.client.get(
            self.url, {"live": False, "facility": self.facility.external_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_external_identifier(self):
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            external_identifier="12345",
        )
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "external_identifier": encounter.external_identifier,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(encounter.external_id))

    def test_filter_encounter_class(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "encounter_class": self.encounter.encounter_class,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    def test_filter_by_priority(self):
        self.get_list_view_permission()
        response = self.client.get(
            self.url,
            {
                "priority": self.encounter.priority,
                "facility": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.encounter.external_id))

    # TESTS FOR VALIDATION
    def test_validate_data_max_encounters(self):
        self.get_list_view_permission()
        for _ in range(settings.MAX_ACTIVE_ENCOUNTERS_PER_PATIENT):
            self.create_encounter(
                patient=self.patient,
                facility=self.facility,
                organization=self.facility_organization,
                status=StatusChoices.in_progress.value,
            )
        # Try to add more that the limit
        response = self.client.post(
            self.url,
            self.encounter_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Patient already has maximum number of active encounters",
            response.data["errors"][0]["msg"],
        )

    def test_validate_data_patient_not_exists(self):
        self.get_list_view_permission()
        self.encounter_data["patient"] = str(uuid.uuid4())  # Non-existent patient
        self.encounter.save()
        response = self.client.post(
            self.url,
            self.encounter_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Patient does not exist", response.data["errors"][0]["msg"])

    def test_validate_data_facility_not_exists(self):
        self.get_list_view_permission()
        self.encounter_data["facility"] = str(uuid.uuid4())  # Non-existent facility
        self.encounter.save()
        response = self.client.post(
            self.url,
            self.encounter_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Facility does not exist", response.data["errors"][0]["msg"])

    # TESTS FOR CRUD OPERATIONS

    def test_create_encounter_with_permissions(self):
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_create_encounter.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        response = self.client.post(self.url, self.encounter_data, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_create_encounter_without_permissions(self):
        response = self.client.post(self.url, self.encounter_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create encounter", response.data["detail"]
        )

    def test_retrieve_encounter_with_permissions(self):
        role = self.create_role_with_permissions(
            permissions=[
                EncounterPermissions.can_read_encounter.name,
                PatientPermissions.can_list_patients.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        response = self.client.get(
            self._get_detail_url(self.facility.external_id, self.patient.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.encounter.external_id))

    def test_retrieve_encounter_without_permissions(self):
        response = self.client.get(
            self._get_detail_url(self.facility.external_id, self.patient.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("User Cannot access patient", response.data["detail"])

    def test_update_encounter_with_permissions(self):
        role = self.create_role_with_permissions(
            permissions=[
                EncounterPermissions.can_write_encounter.name,
                EncounterPermissions.can_read_encounter.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        update_data = self.encounter_data.copy()
        update_data["status"] = StatusChoices.completed.value
        response = self.client.put(
            self._get_detail_url(self.facility.external_id, self.patient.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], StatusChoices.completed.value)


class EncounterOrganizationAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("encounter-list")

    def _get_detail_url(self, path):
        url = reverse(
            "encounter-detail", kwargs={"external_id": self.encounter.external_id}
        )
        url += f"{path}/"
        return url

    def get_role_with_permissions(self):
        role = self.create_role_with_permissions(
            permissions=[
                EncounterPermissions.can_write_encounter.name,
                EncounterPermissions.can_read_encounter.name,
                PatientPermissions.can_view_clinical_data.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )

    def test_list_encounter_organizations_with_permissions(self):
        self.get_role_with_permissions()
        path = "organizations"
        response = self.client.get(self._get_detail_url(path), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_encounter_organizations_without_permissions(self):
        path = "organizations"
        response = self.client.get(self._get_detail_url(path), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update encounter", response.data["detail"]
        )

    def test_add_encounter_organization_with_permissions(self):
        self.get_role_with_permissions()
        new_organization = self.create_facility_organization(facility=self.facility)
        path = "organizations_add"
        response = self.client.post(
            self._get_detail_url(path),
            {"organization": str(new_organization.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(new_organization.external_id))

    def test_add_encounter_organization_without_permissions(self):
        new_organization = self.create_facility_organization(facility=self.facility)
        path = "organizations_add"
        response = self.client.post(
            self._get_detail_url(path),
            {"organization": str(new_organization.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update encounter", response.data["detail"]
        )

    def test_remove_encounter_organization_with_permissions(self):
        self.get_role_with_permissions()
        path = "organizations_remove"
        response = self.client.delete(
            self._get_detail_url(path),
            {"organization": str(self.facility_organization.external_id)},
            format="json",
        )
        path_get = "organizations"
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            self._get_detail_url(path_get),
            format="json",
        )
        # to check if the organization is removed
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_remove_encounter_organization_without_permissions(self):
        path = "organizations_remove"
        response = self.client.delete(
            self._get_detail_url(path),
            {"organization": str(self.facility_organization.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update encounter", response.data["detail"]
        )

    def test_remove_encounter_invalid_organization(self):
        self.get_role_with_permissions()
        path = "organizations_remove"
        response = self.client.delete(
            self._get_detail_url(path),
            {"organization": str(uuid.uuid4())},  # Non-existent organization
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_remove_encounter_organization_incompatible(self):
        self.get_role_with_permissions()
        new_facility = self.create_facility(user=self.user)
        new_organization = self.create_facility_organization(facility=new_facility)
        path = "organizations_remove"
        response = self.client.delete(
            self._get_detail_url(path),
            {"organization": str(new_organization.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "Organization Incompatible with Encounter", response.data["detail"]
        )

    def test_generate_discharge_summary_with_permissions(self):
        self.patient.year_of_birth = 2000
        self.patient.save()
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_view_clinical_data.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        # 3. Mock the necessary functions to isolate the test
        with (
            patch(
                "care.emr.reports.discharge_summary.get_progress"
            ) as mock_get_progress,
            patch("care.emr.reports.discharge_summary.set_lock") as mock_set_lock,
            patch(
                "care.emr.tasks.discharge_summary.generate_discharge_summary_task.delay"
            ) as mock_task,
        ):
            mock_get_progress.return_value = None

            path = "generate_discharge_summary"
            url = self._get_detail_url(path)
            response = self.client.post(
                url, {"external_id": str(self.encounter.external_id)}, format="json"
            )
            self.assertEqual(response.status_code, 202)
            self.assertIn(
                "Discharge Summary will be generated shortly", response.data["detail"]
            )

        mock_get_progress.assert_called_once_with(self.encounter.external_id)
        mock_set_lock.assert_called_once_with(self.encounter.external_id, 1)
        mock_task.assert_called_once_with(self.encounter.external_id)

    def test_generate_discharge_summary_without_permissions(self):
        path = "generate_discharge_summary"
        url = self._get_detail_url(path)
        response = self.client.post(
            url, {"external_id": str(self.encounter.external_id)}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Permission denied to user", response.data["detail"])

    def test_generate_discharge_summary_with_conflict(self):
        self.patient.year_of_birth = 2000
        self.patient.save()
        self.get_role_with_permissions()
        with patch(
            "care.emr.reports.discharge_summary.get_progress"
        ) as mock_get_progress:
            # Return 75% to simulate a discharge summary that's already being generated
            mock_get_progress.return_value = 75

            path = "generate_discharge_summary"
            url = self._get_detail_url(path)
            response = self.client.post(
                url, {"external_id": str(self.encounter.external_id)}, format="json"
            )
            self.assertEqual(response.status_code, 409)
            self.assertIn(
                "Discharge Summary is already being generated", response.data["detail"]
            )
            self.assertIn("75%", response.data["detail"])

    # TESTS FOR CARE TEAM MANAGEMENT

    def test_add_care_team_member_with_permissions(self):
        self.get_role_with_permissions()
        new_user = self.create_user()
        path = "set_care_team_members"
        response = self.client.post(
            self._get_detail_url(path),
            {
                "members": [
                    {
                        "user_id": str(new_user.external_id),
                        "role": {"code": "NURSE", "system": "local"},
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_add_care_team_member_without_permissions(self):
        new_user = self.create_user()
        path = "set_care_team_members"
        response = self.client.post(
            self._get_detail_url(path),
            {
                "members": [
                    {
                        "user_id": str(new_user.external_id),
                        "role": {"code": "NURSE", "system": "local"},
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update encounter", response.data["detail"]
        )

    def test_add_duplicate_user_care_team_member(self):
        self.get_role_with_permissions()
        new_user = self.create_user()
        path = "set_care_team_members"
        response = self.client.post(
            self._get_detail_url(path),
            {
                "members": [
                    {
                        "user_id": str(new_user.external_id),
                        "role": {"code": "NURSE", "system": "local"},
                    },
                    {
                        "user_id": str(new_user.external_id),
                        "role": {"code": "NURSE", "system": "local"},
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "repeats are not allowed", response.data["errors"][0]["msg"]["user"]
        )

    def test_add_treating_doctor_care_team_member(self):
        role = self.create_role_with_permissions(
            permissions=[
                EncounterPermissions.can_write_encounter.name,
                PatientPermissions.can_view_clinical_data.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )

        path = "set_care_team_members"
        new_user = self.create_user()
        response = self.client.post(
            self._get_detail_url(path),
            {
                "members": [
                    {
                        "user_id": str(new_user.external_id),
                        "role": {"code": "TREATING_DOCTOR", "system": "local"},
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "Treating doctor does not have permission on encounter",
            response.data["detail"],
        )
