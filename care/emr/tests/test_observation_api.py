import uuid

from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.observation import Observation
from care.emr.models.questionnaire import QuestionnaireResponse
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.encounter.constants import StatusChoices
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

    def _get_create_data(self, **kwargs):
        data = {
            "encounter": str(self.encounter.external_id),
            "main_code": {
                "system": "http://loinc.org",
                "code": "8480-6",
                "display": "Systolic blood pressure",
            },
            "effective_datetime": timezone.now().isoformat(),
            "value_type": QuestionType.integer.value,
            "value": {"value": "120"},
        }
        data.update(kwargs)
        return data

    def _create_diagnostic_report(self):
        service_request = baker.make(
            ServiceRequest,
            patient=self.patient,
            encounter=self.encounter,
            facility=self.facility,
        )
        return baker.make(
            DiagnosticReport,
            patient=self.patient,
            encounter=self.encounter,
            facility=self.facility,
            service_request=service_request,
        )

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

    def test_list_filter_by_status(self):
        self._grant_patient_read_permission()
        final = self._create_observation(status=ObservationStatus.final.value)
        self._create_observation(status=ObservationStatus.amended.value)
        self._create_observation(status=ObservationStatus.entered_in_error.value)

        response = self.client.get(
            self.base_url, {"status": ObservationStatus.final.value}
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(final.external_id))

    def test_list_filter_by_multiple_statuses(self):
        self._grant_patient_read_permission()
        self._create_observation(status=ObservationStatus.final.value)
        self._create_observation(status=ObservationStatus.amended.value)
        self._create_observation(status=ObservationStatus.entered_in_error.value)

        response = self.client.get(
            self.base_url,
            {
                "status": f"{ObservationStatus.final.value},"
                f"{ObservationStatus.amended.value}"
            },
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(
            {r["status"] for r in results},
            {ObservationStatus.final.value, ObservationStatus.amended.value},
        )

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

    # ── CREATE ───────────────────────────────────────────────────────────

    def test_create_random_observation_with_clinical_write_permission(self):
        self._grant_encounter_write_permission()
        data = self._get_create_data(note="Recorded directly")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        observation = Observation.objects.get(external_id=response.data["id"])
        self.assertEqual(observation.patient, self.patient)
        self.assertEqual(observation.encounter, self.encounter)
        self.assertEqual(observation.subject_id, self.encounter.external_id)
        self.assertEqual(observation.subject_type, SubjectType.encounter.value)
        self.assertEqual(observation.status, ObservationStatus.final.value)
        self.assertEqual(observation.value, data["value"])
        self.assertEqual(observation.main_code, data["main_code"])
        self.assertEqual(observation.note, data["note"])
        self.assertEqual(observation.data_entered_by, self.user)
        self.assertEqual(observation.created_by, self.user)
        self.assertEqual(observation.updated_by, self.user)
        self.assertIsNone(observation.questionnaire_response)
        self.assertIsNone(observation.diagnostic_report)
        self.assertTrue(response.data["is_random"])

    def test_create_without_permissions(self):
        response = self.client.post(
            self.base_url, self._get_create_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Observation.objects.exists())

    def test_create_with_read_only_permission(self):
        self._grant_patient_read_permission()
        self._grant_encounter_read_permission()
        response = self.client.post(
            self.base_url, self._get_create_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Observation.objects.exists())

    def test_create_with_other_patients_encounter(self):
        self._grant_encounter_write_permission()
        other_encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=self.facility,
            organization=self.organization,
        )
        response = self.client.post(
            self.base_url,
            self._get_create_data(encounter=str(other_encounter.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Observation.objects.exists())

    def test_create_with_nonexistent_encounter(self):
        self._grant_encounter_write_permission()
        response = self.client.post(
            self.base_url,
            self._get_create_data(encounter=str(uuid.uuid4())),
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Observation.objects.exists())

    def test_create_with_missing_encounter(self):
        self._grant_encounter_write_permission()
        data = self._get_create_data()
        del data["encounter"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Observation.objects.exists())

    def test_create_requires_observation_code_time_and_value(self):
        self._grant_encounter_write_permission()
        for field in ("main_code", "effective_datetime", "value_type", "value"):
            with self.subTest(field=field):
                data = self._get_create_data()
                del data[field]
                response = self.client.post(self.base_url, data, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Observation.objects.exists())

    def test_create_requires_timezone_aware_time(self):
        self._grant_encounter_write_permission()
        response = self.client.post(
            self.base_url,
            self._get_create_data(effective_datetime="2026-10-25T10:30:00"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Observation.objects.exists())

    def test_create_rejects_nonfinal_status(self):
        self._grant_encounter_write_permission()
        for status in (
            ObservationStatus.amended.value,
            ObservationStatus.entered_in_error.value,
        ):
            with self.subTest(status=status):
                response = self.client.post(
                    self.base_url,
                    self._get_create_data(status=status),
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Observation.objects.exists())

    def test_create_rejects_source_and_audit_fields(self):
        self._grant_encounter_write_permission()
        for field, value in (
            ("id", str(uuid.uuid4())),
            ("questionnaire_response", str(uuid.uuid4())),
            ("diagnostic_report", str(uuid.uuid4())),
            ("parent", str(uuid.uuid4())),
            ("created_by_id", self.user.id),
            ("data_entered_by_id", self.user.id),
            ("is_random", False),
            ("meta", {"source": "questionnaire"}),
        ):
            with self.subTest(field=field):
                response = self.client.post(
                    self.base_url,
                    self._get_create_data(**{field: value}),
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Observation.objects.exists())

    def test_create_in_completed_encounter(self):
        self._grant_encounter_write_permission()
        self.encounter.status = StatusChoices.completed.value
        self.encounter.save(update_fields=["status"])
        response = self.client.post(
            self.base_url, self._get_create_data(), format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Observation.objects.exists())

    # ── MARK ENTERED IN ERROR ────────────────────────────────────────────

    def test_delete_marks_random_observation_entered_in_error(self):
        self._grant_encounter_write_permission()
        original_author = self.create_user()
        obs = self._create_observation(
            created_by=original_author, data_entered_by=original_author
        )
        original_value = obs.value.copy()
        original_modified_date = obs.modified_date
        url = self._get_detail_url(obs.external_id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.entered_in_error.value)
        self.assertEqual(obs.updated_by, self.user)
        self.assertGreater(obs.modified_date, original_modified_date)
        self.assertEqual(obs.created_by, original_author)
        self.assertEqual(obs.data_entered_by, original_author)
        self.assertEqual(obs.value, original_value)
        self.assertFalse(obs.deleted)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.entered_in_error.value)
        self.assertFalse(obs.deleted)
        self.assertEqual(obs.value, original_value)

    def test_mark_entered_in_error_without_permissions(self):
        obs = self._create_observation()
        response = self.client.delete(self._get_detail_url(obs.external_id))
        self.assertEqual(response.status_code, 403)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.final.value)
        self.assertFalse(obs.deleted)

    def test_mark_entered_in_error_with_read_only_permission(self):
        self._grant_patient_read_permission()
        self._grant_encounter_read_permission()
        obs = self._create_observation()
        response = self.client.delete(self._get_detail_url(obs.external_id))
        self.assertEqual(response.status_code, 403)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.final.value)
        self.assertFalse(obs.deleted)

    def test_cannot_mark_questionnaire_observation_entered_in_error(self):
        self._grant_encounter_write_permission()
        questionnaire_response = baker.make(
            QuestionnaireResponse, patient=self.patient, encounter=self.encounter
        )
        obs = self._create_observation(questionnaire_response=questionnaire_response)
        response = self.client.delete(self._get_detail_url(obs.external_id))
        self.assertEqual(response.status_code, 400)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.final.value)
        self.assertFalse(obs.deleted)

    def test_cannot_mark_diagnostic_report_observation_entered_in_error(self):
        self._grant_encounter_write_permission()
        report = self._create_diagnostic_report()
        obs = self._create_observation(diagnostic_report=report)
        response = self.client.delete(self._get_detail_url(obs.external_id))
        self.assertEqual(response.status_code, 400)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.final.value)
        self.assertFalse(obs.deleted)

    def test_mark_entered_in_error_under_wrong_patient(self):
        self._grant_encounter_write_permission()
        obs = self._create_observation()
        response = self.client.delete(
            self._get_detail_url(obs.external_id, patient=self.create_patient())
        )
        self.assertEqual(response.status_code, 404)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.final.value)
        self.assertFalse(obs.deleted)

    def test_update_not_supported(self):
        self._grant_encounter_write_permission()
        obs = self._create_observation()
        for method in (self.client.put, self.client.patch):
            with self.subTest(method=method.__name__):
                response = method(
                    self._get_detail_url(obs.external_id),
                    {"status": ObservationStatus.entered_in_error.value},
                    format="json",
                )
                self.assertEqual(response.status_code, 405)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.final.value)
        self.assertFalse(obs.deleted)

    def test_mark_entered_in_error_in_completed_encounter(self):
        self._grant_encounter_write_permission()
        obs = self._create_observation()
        self.encounter.status = StatusChoices.completed.value
        self.encounter.save(update_fields=["status"])
        response = self.client.delete(self._get_detail_url(obs.external_id))
        self.assertEqual(response.status_code, 403)
        obs.refresh_from_db()
        self.assertEqual(obs.status, ObservationStatus.final.value)
        self.assertFalse(obs.deleted)

    def test_read_indicates_observation_origin(self):
        self._grant_patient_read_permission()
        random = self._create_observation()
        questionnaire_response = baker.make(
            QuestionnaireResponse, patient=self.patient, encounter=self.encounter
        )
        structured = self._create_observation(
            questionnaire_response=questionnaire_response
        )
        report_observation = self._create_observation(
            diagnostic_report=self._create_diagnostic_report()
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        by_id = {result["id"]: result for result in response.data["results"]}
        self.assertTrue(by_id[str(random.external_id)]["is_random"])
        self.assertFalse(by_id[str(structured.external_id)]["is_random"])
        self.assertFalse(by_id[str(report_observation.external_id)]["is_random"])

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
