import uuid

from django.urls import reverse
from model_bakery import baker

from care.emr.models.observation import Observation
from care.emr.resources.observation.spec import ObservationStatus
from care.emr.resources.questionnaire.spec import QuestionType, SubjectType
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class TestObservationViewSet(CareAPITestBase):
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
            "observation-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )

    def _get_detail_url(self, external_id, patient=None):
        return reverse(
            "observation-detail",
            kwargs={
                "patient_external_id": (patient or self.patient).external_id,
                "external_id": external_id,
            },
        )

    def _get_analyse_url(self, patient=None):
        return reverse(
            "observation-analyse",
            kwargs={
                "patient_external_id": (patient or self.patient).external_id,
            },
        )

    def _create_observation(self, patient=None, encounter=None, **kwargs):
        defaults = {
            "patient": patient or self.patient,
            "encounter": encounter or self.encounter,
            "status": ObservationStatus.final.value,
            "value_type": QuestionType.integer.value,
            "value": {"value": "120"},
            "main_code": {"system": "http://loinc.org", "code": "8480-6"},
            "subject_type": SubjectType.encounter.value,
            "subject_id": (encounter or self.encounter).external_id,
            "note": "",
        }
        defaults.update(kwargs)
        return baker.make(Observation, **defaults)

    def _grant_patient_read_permission(self):
        role = self.create_role_with_permissions(
            [PatientPermissions.can_view_clinical_data.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    def _grant_encounter_read_permission(self):
        role = self.create_role_with_permissions(
            [EncounterPermissions.can_read_encounter_clinical_data.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    def _grant_encounter_write_permission(self):
        role = self.create_role_with_permissions(
            [EncounterPermissions.can_write_encounter_clinical_data.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    # ── LIST ─────────────────────────────────────────────────────────────

    def test_list_without_permissions(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_with_patient_read_permission(self):
        self._grant_patient_read_permission()
        self._create_observation()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_list_with_encounter_filter_and_encounter_permission(self):
        self._grant_encounter_read_permission()
        self._create_observation()
        response = self.client.get(
            self.base_url, {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_list_without_encounter_filter_no_patient_perm(self):
        self._grant_encounter_read_permission()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_with_invalid_encounter_filter(self):
        self._grant_encounter_read_permission()
        response = self.client.get(self.base_url, {"encounter": uuid.uuid4()})
        self.assertEqual(response.status_code, 404)

    def test_list_returns_only_matching_patient(self):
        self._grant_patient_read_permission()
        obs = self._create_observation()

        other_patient = self.create_patient()
        other_encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.organization,
        )
        self._create_observation(patient=other_patient, encounter=other_encounter)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(obs.external_id))

    def test_list_filter_by_encounter(self):
        self._grant_patient_read_permission()
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self._create_observation(encounter=self.encounter)
        self._create_observation(encounter=other_encounter)

        response = self.client.get(
            self.base_url, {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_list_filter_by_codes(self):
        self._grant_patient_read_permission()
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "8480-6"}
        )
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "8462-4"}
        )
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "9999-9"}
        )

        response = self.client.get(self.base_url, {"codes": "8480-6,8462-4"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 2)

    def test_list_filter_ignore_group(self):
        self._grant_patient_read_permission()
        self._create_observation(value_type=QuestionType.integer.value)
        self._create_observation(value_type=QuestionType.group.value, value={})

        response = self.client.get(self.base_url, {"ignore_group": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_list_ordered_by_modified_date_descending(self):
        self._grant_patient_read_permission()
        obs1 = self._create_observation()
        obs2 = self._create_observation()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], str(obs2.external_id))
        self.assertEqual(results[1]["id"], str(obs1.external_id))

    def test_list_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_list_with_nonexistent_patient(self):
        self._grant_patient_read_permission()
        url = reverse(
            "observation-list",
            kwargs={"patient_external_id": uuid.uuid4()},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # ── RETRIEVE ─────────────────────────────────────────────────────────

    def test_retrieve_with_patient_read_permission(self):
        self._grant_patient_read_permission()
        obs = self._create_observation()
        url = self._get_detail_url(obs.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(obs.external_id))

    def test_retrieve_with_encounter_read_permission(self):
        self._grant_encounter_read_permission()
        obs = self._create_observation()
        url = self._get_detail_url(obs.external_id)
        response = self.client.get(url, {"encounter": self.encounter.external_id})
        self.assertEqual(response.status_code, 200)

    def test_retrieve_without_permissions(self):
        obs = self._create_observation()
        url = self._get_detail_url(obs.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_retrieve_nonexistent(self):
        self._grant_patient_read_permission()
        url = self._get_detail_url(uuid.uuid4())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_retrieve_includes_observation_definition(self):
        self._grant_patient_read_permission()
        obs = self._create_observation()
        url = self._get_detail_url(obs.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("observation_definition", response.json())

    # ── CREATE / UPDATE / DELETE (not supported) ─────────────────────────

    def test_create_not_supported(self):
        self._grant_encounter_write_permission()
        data = {
            "status": ObservationStatus.final.value,
            "value_type": QuestionType.integer.value,
            "value": {"value": "120"},
            "encounter": str(self.encounter.external_id),
        }
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 405)

    def test_update_not_supported(self):
        self._grant_encounter_write_permission()
        obs = self._create_observation()
        url = self._get_detail_url(obs.external_id)
        response = self.client.put(
            url, {"status": ObservationStatus.amended.value}, format="json"
        )
        self.assertEqual(response.status_code, 405)

    def test_delete_not_supported(self):
        self._grant_encounter_write_permission()
        obs = self._create_observation()
        url = self._get_detail_url(obs.external_id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 405)

    # ── ANALYSE ACTION ───────────────────────────────────────────────────

    def test_analyse_without_permissions(self):
        url = self._get_analyse_url()
        data = {
            "codes": [{"system": "http://loinc.org", "code": "8480-6"}],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_analyse_with_permissions(self):
        self._grant_patient_read_permission()
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "8480-6"}
        )
        url = self._get_analyse_url()
        data = {
            "codes": [{"system": "http://loinc.org", "code": "8480-6"}],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code"]["code"], "8480-6")
        self.assertEqual(len(results[0]["results"]), 1)

    def test_analyse_multiple_codes(self):
        self._grant_patient_read_permission()
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "8480-6"}
        )
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "8462-4"}
        )
        url = self._get_analyse_url()
        data = {
            "codes": [
                {"system": "http://loinc.org", "code": "8480-6"},
                {"system": "http://loinc.org", "code": "8462-4"},
            ],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 2)

    def test_analyse_returns_matching_code_only(self):
        self._grant_patient_read_permission()
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "8480-6"}
        )
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "9999-9"}
        )
        url = self._get_analyse_url()
        data = {
            "codes": [{"system": "http://loinc.org", "code": "8480-6"}],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0]["results"]), 1)

    def test_analyse_respects_page_size(self):
        self._grant_patient_read_permission()
        for _ in range(5):
            self._create_observation(
                main_code={"system": "http://loinc.org", "code": "8480-6"}
            )
        url = self._get_analyse_url()
        data = {
            "codes": [{"system": "http://loinc.org", "code": "8480-6"}],
            "page_size": 2,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results[0]["results"]), 2)

    def test_analyse_empty_codes_rejected(self):
        self._grant_patient_read_permission()
        url = self._get_analyse_url()
        data = {"codes": []}
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [400, 422])

    def test_analyse_no_matching_observations(self):
        self._grant_patient_read_permission()
        url = self._get_analyse_url()
        data = {
            "codes": [{"system": "http://loinc.org", "code": "nonexistent"}],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0]["results"]), 0)

    def test_analyse_with_encounter_filter_permission(self):
        self._grant_encounter_read_permission()
        self._create_observation(
            main_code={"system": "http://loinc.org", "code": "8480-6"}
        )
        url = self._get_analyse_url()
        data = {
            "codes": [{"system": "http://loinc.org", "code": "8480-6"}],
        }
        response = self.client.post(
            url,
            data,
            format="json",
            QUERY_STRING=f"encounter={self.encounter.external_id}",
        )
        self.assertEqual(response.status_code, 200)
