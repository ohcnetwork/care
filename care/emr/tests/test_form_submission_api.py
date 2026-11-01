import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import skipUnlessDBFeature
from django.urls import reverse
from model_bakery import baker
from rest_framework import status as http_status
from rest_framework.test import APIClient, APITransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from care.emr.api.viewsets.form_submission import FormSubmissionViewSet
from care.emr.models import Condition, Encounter, Patient
from care.emr.models.questionnaire import FormSubmission, Questionnaire
from care.emr.resources.encounter.constants import StatusChoices
from care.emr.resources.form_submission.spec import FormSubmissionStatusChoices
from care.facility.models.facility import Facility
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.users.models import User
from care.utils.tests.base import CareAPITestBase


class TestFormSubmissionViewSet(CareAPITestBase):
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
        self.questionnaire = baker.make(
            Questionnaire,
            slug="test-questionnaire",
            title="Test Questionnaire",
        )
        self.client.force_authenticate(user=self.user)
        self.base_url = reverse("form_submission-list")

    def _get_detail_url(self, external_id):
        return reverse(
            "form_submission-detail",
            kwargs={"external_id": external_id},
        )

    def _create_form_submission(self, patient=None, encounter=None, **kwargs):
        data = {
            "questionnaire": self.questionnaire,
            "patient": patient or self.patient,
            "status": FormSubmissionStatusChoices.draft.value,
            "response_dump": {"key": "value"},
        }
        if encounter:
            data["encounter"] = encounter
        data.update(kwargs)
        return baker.make(FormSubmission, **data)

    def _generate_create_data(self, encounter=None, patient=None, **kwargs):
        data = {
            "questionnaire": str(self.questionnaire.external_id),
            "patient": str((patient or self.patient).external_id),
            "status": FormSubmissionStatusChoices.draft.value,
            "response_dump": {"answer": 42},
        }
        if encounter:
            data["encounter"] = str(encounter.external_id)
        data.update(kwargs)
        return data

    def _grant_patient_submit_permission(self):
        permissions = [PatientPermissions.can_submit_patient_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    def _grant_encounter_submit_permission(self):
        permissions = [EncounterPermissions.can_submit_encounter_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    # ── LIST ─────────────────────────────────────────────────────────────

    def test_list_without_patient_or_encounter_filter(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 400)

    def test_list_with_patient_filter_without_permissions(self):
        response = self.client.get(self.base_url, {"patient": self.patient.external_id})
        self.assertEqual(response.status_code, 403)

    def test_list_with_patient_filter_with_permissions(self):
        self._grant_patient_submit_permission()
        self._create_form_submission()
        response = self.client.get(self.base_url, {"patient": self.patient.external_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_list_with_encounter_filter_without_permissions(self):
        response = self.client.get(
            self.base_url, {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 403)

    def test_list_with_encounter_filter_with_permissions(self):
        self._grant_encounter_submit_permission()
        self._create_form_submission(encounter=self.encounter)
        response = self.client.get(
            self.base_url, {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_list_with_encounter_filter_completed_encounter(self):
        self._grant_encounter_submit_permission()
        completed_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        response = self.client.get(
            self.base_url, {"encounter": completed_encounter.external_id}
        )
        self.assertEqual(response.status_code, 403)

    def test_list_filtered_by_patient_returns_only_matching(self):
        self._grant_patient_submit_permission()
        submission = self._create_form_submission()

        other_patient = self.create_patient()
        other_encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.organization,
        )
        self._create_form_submission(patient=other_patient, encounter=other_encounter)

        response = self.client.get(self.base_url, {"patient": self.patient.external_id})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(submission.external_id))

    def test_list_filtered_by_encounter_returns_only_matching(self):
        self._grant_encounter_submit_permission()
        submission = self._create_form_submission(encounter=self.encounter)

        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self._create_form_submission(encounter=other_encounter)

        response = self.client.get(
            self.base_url, {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(submission.external_id))

    def test_list_filter_by_status(self):
        self._grant_patient_submit_permission()
        self._create_form_submission(status=FormSubmissionStatusChoices.draft.value)
        self._create_form_submission(status=FormSubmissionStatusChoices.submitted.value)

        response = self.client.get(
            self.base_url,
            {
                "patient": self.patient.external_id,
                "status": FormSubmissionStatusChoices.draft.value,
            },
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], FormSubmissionStatusChoices.draft.value)

    def test_list_filter_by_questionnaire_slug(self):
        self._grant_patient_submit_permission()
        self._create_form_submission()

        other_questionnaire = baker.make(Questionnaire, slug="other-questionnaire")
        self._create_form_submission(questionnaire=other_questionnaire)

        response = self.client.get(
            self.base_url,
            {
                "patient": self.patient.external_id,
                "questionnaire": self.questionnaire.slug,
            },
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)

    def test_list_with_invalid_patient_uuid(self):
        response = self.client.get(self.base_url, {"patient": uuid.uuid4()})
        self.assertEqual(response.status_code, 404)

    def test_list_with_invalid_encounter_uuid(self):
        response = self.client.get(self.base_url, {"encounter": uuid.uuid4()})
        self.assertEqual(response.status_code, 404)

    # ── CREATE ───────────────────────────────────────────────────────────

    def test_create_with_patient_permissions(self):
        self._grant_patient_submit_permission()
        data = self._generate_create_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["status"], FormSubmissionStatusChoices.draft.value
        )

    def test_create_with_encounter_permissions(self):
        self._grant_encounter_submit_permission()
        data = self._generate_create_data(encounter=self.encounter)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_without_permissions(self):
        data = self._generate_create_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_unauthenticated(self):
        self.client.logout()
        data = self._generate_create_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_with_encounter_sets_patient_from_encounter(self):
        self._grant_encounter_submit_permission()
        other_patient = self.create_patient()
        data = self._generate_create_data(
            encounter=self.encounter, patient=other_patient
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        submission = FormSubmission.objects.order_by("-id").first()
        self.assertEqual(submission.patient, self.encounter.patient)

    def test_create_with_completed_encounter(self):
        self._grant_encounter_submit_permission()
        completed_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        data = self._generate_create_data(encounter=completed_encounter)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_with_invalid_questionnaire_uuid(self):
        self._grant_patient_submit_permission()
        data = self._generate_create_data()
        data["questionnaire"] = str(uuid.uuid4())
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 404)

    def test_create_with_invalid_patient_uuid(self):
        self._grant_patient_submit_permission()
        data = self._generate_create_data()
        data["patient"] = str(uuid.uuid4())
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 404)

    def test_create_with_invalid_encounter_uuid(self):
        self._grant_encounter_submit_permission()
        data = self._generate_create_data(encounter=self.encounter)
        data["encounter"] = str(uuid.uuid4())
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 404)

    def test_create_stores_response_dump(self):
        self._grant_patient_submit_permission()
        response_dump = {"q1": "yes", "q2": [1, 2, 3]}
        data = self._generate_create_data(response_dump=response_dump)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response_dump"], response_dump)

    # ── RETRIEVE ─────────────────────────────────────────────────────────

    def test_retrieve_with_encounter_permissions(self):
        self._grant_encounter_submit_permission()
        submission = self._create_form_submission(encounter=self.encounter)
        url = self._get_detail_url(submission.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(submission.external_id))

    def test_retrieve_with_patient_permissions(self):
        self._grant_patient_submit_permission()
        submission = self._create_form_submission()
        url = self._get_detail_url(submission.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_retrieve_without_permissions(self):
        submission = self._create_form_submission(encounter=self.encounter)
        url = self._get_detail_url(submission.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_retrieve_nonexistent(self):
        self._grant_encounter_submit_permission()
        url = self._get_detail_url(uuid.uuid4())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # ── UPDATE ───────────────────────────────────────────────────────────

    def test_update_with_encounter_permissions(self):
        self._grant_encounter_submit_permission()
        submission = self._create_form_submission(encounter=self.encounter)
        url = self._get_detail_url(submission.external_id)
        update_data = {
            "status": FormSubmissionStatusChoices.submitted.value,
            "response_dump": {"updated": True},
        }
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["status"], FormSubmissionStatusChoices.submitted.value
        )
        self.assertEqual(response.json()["response_dump"], {"updated": True})

    def test_update_with_patient_permissions(self):
        self._grant_patient_submit_permission()
        for initial_status in ("draft", "submitted"):
            with self.subTest(initial_status=initial_status):
                submission = self._create_form_submission(status=initial_status)
                url = self._get_detail_url(submission.external_id)
                update_data = {
                    "status": FormSubmissionStatusChoices.submitted.value,
                    "response_dump": {"updated": True},
                }
                response = self.client.put(url, update_data, format="json")
                self.assertEqual(response.status_code, 200)
                submission.refresh_from_db()
                self.assertEqual(submission.response_dump, {"updated": True})

    def test_update_without_permissions(self):
        submission = self._create_form_submission(encounter=self.encounter)
        url = self._get_detail_url(submission.external_id)
        update_data = {
            "status": FormSubmissionStatusChoices.submitted.value,
            "response_dump": {},
        }
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_update_completed_encounter(self):
        self._grant_encounter_submit_permission()
        completed_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status=StatusChoices.completed.value,
        )
        submission = self._create_form_submission(encounter=completed_encounter)
        url = self._get_detail_url(submission.external_id)
        update_data = {
            "status": FormSubmissionStatusChoices.submitted.value,
            "response_dump": {},
        }
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_update_to_entered_in_error(self):
        self._grant_encounter_submit_permission()
        submission = self._create_form_submission(encounter=self.encounter)
        url = self._get_detail_url(submission.external_id)
        update_data = {
            "status": FormSubmissionStatusChoices.entered_in_error.value,
            "response_dump": {},
        }
        response = self.client.put(url, update_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["status"],
            FormSubmissionStatusChoices.entered_in_error.value,
        )

    # ── DELETE (unsupported) ─────────────────────────────────────────────

    def test_delete_not_supported(self):
        self._grant_encounter_submit_permission()
        submission = self._create_form_submission(encounter=self.encounter)
        url = self._get_detail_url(submission.external_id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 405)


class TestFormSubmissionCompletionConcurrency(APITransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_structured_completion_commits_only_one_batch(self):
        user = baker.make(User, is_superuser=True)
        patient = baker.make(Patient)
        facility = baker.make(Facility, created_by=user)
        encounter = baker.make(
            Encounter,
            patient=patient,
            facility=facility,
            status=StatusChoices.in_progress.value,
        )
        submission = baker.make(
            FormSubmission,
            patient=patient,
            encounter=encounter,
            status="draft",
            response_dump={},
        )
        user.get_cached_role_orgs()
        token = str(AccessToken.for_user(user))
        completion_url = reverse(
            "form_submission-detail",
            kwargs={"external_id": submission.external_id},
        )
        diagnosis_url = reverse(
            "diagnosis-list", kwargs={"patient_external_id": patient.external_id}
        )
        barrier = Barrier(2)
        original_update = FormSubmissionViewSet.update

        def complete_together(view, *args, **kwargs):
            # Both batches have written their diagnosis before either completes.
            barrier.wait(timeout=10)
            return original_update(view, *args, **kwargs)

        def submit(marker):
            close_old_connections()
            try:
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
                response = client.post(
                    reverse("batch-requests-list"),
                    {
                        "requests": [
                            {
                                "url": diagnosis_url,
                                "method": "POST",
                                "reference_id": "diagnosis",
                                "body": {
                                    "encounter": str(encounter.external_id),
                                    "form_submission": str(submission.external_id),
                                    "category": "encounter_diagnosis",
                                    "clinical_status": "active",
                                    "verification_status": "confirmed",
                                    "severity": "mild",
                                    "code": {
                                        "display": "Test diagnosis",
                                        "system": "http://test_system.care/test",
                                        "code": "123",
                                    },
                                    "note": marker,
                                },
                            },
                            {
                                "url": completion_url,
                                "method": "PUT",
                                "reference_id": "completion",
                                "body": {
                                    "expected_status": "draft",
                                    "status": "submitted",
                                    "response_dump": {"marker": marker},
                                },
                            },
                        ]
                    },
                    format="json",
                )
                return response.status_code, response.json()
            finally:
                close_old_connections()

        with (
            patch.object(FormSubmissionViewSet, "update", complete_together),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            responses = list(executor.map(submit, ("first", "second")))

        self.assertCountEqual([status for status, _ in responses], [200, 400])
        failed = next(
            body
            for status, body in responses
            if status == http_status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(failed["results"][0]["status_code"], 200)
        self.assertEqual(failed["results"][1]["status_code"], 400)
        self.assertEqual(
            failed["results"][1]["data"]["errors"][0]["msg"],
            "Form submission status has changed",
        )
        diagnosis = Condition.objects.get(patient=patient)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "submitted")
        self.assertEqual(submission.response_dump, {"marker": diagnosis.note})
