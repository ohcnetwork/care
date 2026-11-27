import uuid
from unittest.mock import patch

from django.db import DatabaseError
from django.urls import reverse
from model_bakery import baker

from care.emr.api.viewsets.base import EMRUpdateMixin
from care.emr.models.observation import Observation
from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.utils.tests.base import CareAPITestBase


class QuestionnaireResponseFilterTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.client.force_authenticate(self.user)
        self.patient = self.create_patient()
        facility = self.create_facility(user=self.user)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=facility,
            organization=self.create_facility_organization(facility=facility),
        )
        self.questionnaire = baker.make(
            Questionnaire,
            auth_context="instance",
            subject_type="encounter",
            status="active",
            questions=[],
            internal_revision=2,
        )
        self.old_questionnaire = baker.make(
            Questionnaire,
            auth_context="instance",
            subject_type="encounter",
            status="active",
            questions=[],
            slug=self.questionnaire.slug,
            latest_revision=self.questionnaire,
            internal_revision=1,
        )
        self.current = self.make_response(self.questionnaire, revision=2)
        self.historical = self.make_response(self.old_questionnaire, revision=1)
        unrelated = baker.make(
            Questionnaire, subject_type="encounter", status="active", questions=[]
        )
        self.unrelated = self.make_response(unrelated)
        self.url = reverse(
            "questionnaire-response-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )

    def make_response(self, questionnaire, **kwargs):
        return baker.make(
            QuestionnaireResponse,
            questionnaire=questionnaire,
            patient=self.patient,
            encounter=self.encounter,
            subject_id=self.encounter.external_id,
            created_by=self.user,
            updated_by=self.user,
            structured_response_type=None,
            **kwargs,
        )

    def result_ids(self, **filters):
        response = self.client.get(self.url, filters)
        self.assertEqual(response.status_code, 200, response.data)
        return {item["id"] for item in response.data["results"]}

    def detail_url(self, response):
        return reverse(
            "questionnaire-response-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": response.external_id,
            },
        )

    def test_latest_questionnaire_filter_includes_historical_revisions(self):
        self.assertEqual(
            self.result_ids(questionnaire=self.questionnaire.external_id),
            {str(self.current.external_id), str(self.historical.external_id)},
        )

    def test_historical_questionnaire_filter_matches_only_that_revision(self):
        self.assertEqual(
            self.result_ids(questionnaire=self.old_questionnaire.external_id),
            {str(self.historical.external_id)},
        )

    def test_nonexistent_questionnaire_filter_returns_no_responses(self):
        self.assertEqual(self.result_ids(questionnaire=uuid.uuid4()), set())

    def test_malformed_questionnaire_filter_is_rejected(self):
        response = self.client.get(self.url, {"questionnaire": "invalid-uuid"})
        self.assertEqual(response.status_code, 400)

    def test_role_filter_uses_submitter_membership_and_excludes_other_submitters(self):
        organization = self.create_organization(org_type="role")
        self.attach_role_organization_user(organization, self.user, self.create_role())
        self.user.refresh_from_db()
        self.assertIn(organization.pk, self.user.role_org_ids)
        other_user = self.create_user()
        QuestionnaireResponse.objects.filter(pk=self.unrelated.pk).update(
            created_by=other_user
        )
        self.assertEqual(
            self.result_ids(role=organization.external_id),
            {str(self.current.external_id), str(self.historical.external_id)},
        )
        self.assertEqual(
            self.result_ids(
                role=organization.external_id, created_by=other_user.external_id
            ),
            set(),
        )

    def test_nonexistent_role_filter_returns_no_responses(self):
        self.assertEqual(self.result_ids(role=uuid.uuid4()), set())

    def test_created_by_filter_returns_only_that_submitters_responses(self):
        other_user = self.create_user()
        QuestionnaireResponse.objects.filter(pk=self.unrelated.pk).update(
            created_by=other_user
        )
        self.assertEqual(
            self.result_ids(created_by=other_user.external_id),
            {str(self.unrelated.external_id)},
        )

    def test_questionnaire_filter_does_not_include_another_patients_responses(self):
        another = self.create_patient()
        QuestionnaireResponse.objects.filter(pk=self.historical.pk).update(
            patient=another
        )
        self.assertEqual(
            self.result_ids(questionnaire=self.questionnaire.external_id),
            {str(self.current.external_id)},
        )

    def make_observation(self, response):
        return baker.make(
            Observation,
            questionnaire_response=response,
            patient=self.patient,
            encounter=self.encounter,
            status="final",
            value={},
        )

    def test_entering_response_in_error_invalidates_only_its_observations(self):
        affected = self.make_observation(self.current)
        unaffected = self.make_observation(self.unrelated)
        response = self.client.patch(
            self.detail_url(self.current), {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.current.refresh_from_db()
        affected.refresh_from_db()
        unaffected.refresh_from_db()
        self.assertEqual(self.current.status, "entered_in_error")
        self.assertEqual(affected.status, "entered_in_error")
        self.assertEqual(unaffected.status, "final")

    def test_unchanged_completed_status_keeps_observations_final(self):
        observation = self.make_observation(self.current)
        response = self.client.patch(
            self.detail_url(self.current), {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        observation.refresh_from_db()
        self.assertEqual(observation.status, "final")

    def test_observation_status_rolls_back_when_response_update_fails(self):
        observation = self.make_observation(self.current)
        with (
            patch.object(
                EMRUpdateMixin,
                "perform_update",
                side_effect=DatabaseError("write failed"),
            ),
            self.assertLogs("django.request", level="ERROR") as logs,
            self.assertRaisesRegex(DatabaseError, "write failed"),
        ):
            self.client.patch(
                self.detail_url(self.current),
                {"status": "entered_in_error"},
                format="json",
            )
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(logs.records[0].status_code, 500)
        self.assertIsInstance(logs.records[0].exc_info[1], DatabaseError)
        self.current.refresh_from_db()
        observation.refresh_from_db()
        self.assertEqual(self.current.status, "completed")
        self.assertEqual(observation.status, "final")
