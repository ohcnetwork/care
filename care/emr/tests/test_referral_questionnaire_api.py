from unittest.mock import patch
from uuid import uuid4

from django.urls import reverse

from care.emr.locks.questionnaire import QuestionnaireLock
from care.emr.models.facility_resource import FacilityResourceQuestionnaireResponse
from care.emr.models.observation import Observation
from care.emr.models.questionnaire import (
    FormSubmission,
    Questionnaire,
    QuestionnaireResponse,
)
from care.utils.tests.base import CareAPITestBase


class ReferralQuestionnaireAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.question = {
            "id": str(uuid4()),
            "link_id": "reason",
            "text": "Reason for referral",
            "type": "text",
            "required": True,
        }
        self.questionnaire = Questionnaire.objects.create(
            title="Referral assessment",
            slug="referral-assessment",
            version="1.0",
            auth_context="instance",
            subject_type="referral",
            status="active",
            questions=[self.question],
        )
        self.client.force_authenticate(user=self.user)

    def questionnaire_url(self, action="detail"):
        return reverse(
            f"questionnaire-{action}",
            kwargs={"external_id": self.questionnaire.external_id},
        )

    def answers(self):
        return [
            {
                "question_id": self.question["id"],
                "values": [{"value": "Specialist assessment"}],
            }
        ]

    def assert_no_submissions(self):
        self.assertFalse(QuestionnaireResponse.objects.exists())
        self.assertFalse(FacilityResourceQuestionnaireResponse.objects.exists())
        self.assertFalse(FormSubmission.objects.exists())
        self.assertFalse(Observation.objects.exists())

    def test_referral_questionnaires_can_be_created_and_retrieved(self):
        created = self.client.post(
            reverse("questionnaire-list"),
            {
                "title": "Referral response assessment",
                "slug": "referral-response-assessment",
                "auth_context": "instance",
                "subject_type": "referral",
                "status": "active",
                "questions": [self.question],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200, created.data)
        self.assertEqual(created.data["subject_type"], "referral")
        questionnaire = Questionnaire.objects.get(external_id=created.data["id"])
        self.assertEqual(questionnaire.subject_type, "referral")
        retrieved = self.client.get(
            reverse(
                "questionnaire-detail",
                kwargs={"external_id": questionnaire.external_id},
            )
        )
        self.assertEqual(retrieved.status_code, 200, retrieved.data)
        self.assertEqual(retrieved.data["subject_type"], "referral")

    def test_referral_questionnaires_can_be_filtered_separately(self):
        for subject_type in ("patient", "encounter", "location", "device", "facility"):
            Questionnaire.objects.create(
                title=f"{subject_type} assessment",
                slug=f"{subject_type}-assessment",
                version="1.0",
                auth_context="instance",
                subject_type=subject_type,
                status="active",
                questions=[self.question],
            )
        response = self.client.get(
            reverse("questionnaire-list"), {"subject_type": "referral"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(self.questionnaire.external_id)
        )

    def test_referral_questionnaires_can_be_updated_without_optional_actions(self):
        with (
            patch.object(QuestionnaireLock, "acquire"),
            patch.object(QuestionnaireLock, "release"),
        ):
            response = self.client.put(
                self.questionnaire_url(),
                {
                    "title": "Updated referral assessment",
                    "status": "active",
                    "questions": [self.question],
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["title"], "Updated referral assessment")
        self.assertEqual(response.data["subject_type"], "referral")
        self.questionnaire.refresh_from_db()
        self.assertEqual(self.questionnaire.title, "Updated referral assessment")
        self.assertEqual(self.questionnaire.subject_type, "referral")
        self.assertEqual(self.questionnaire.actions, [])

    def test_referral_forms_cannot_be_submitted_as_patient_or_encounter_responses(self):
        for with_encounter in (False, True):
            with self.subTest(with_encounter=with_encounter):
                payload = {
                    "resource_id": str(self.patient.external_id),
                    "patient": str(self.patient.external_id),
                    "results": self.answers(),
                }
                if with_encounter:
                    payload["encounter"] = str(self.encounter.external_id)
                response = self.client.post(
                    self.questionnaire_url("submit"), payload, format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("referral", str(response.data).lower())
                self.assert_no_submissions()

    def test_referral_forms_cannot_be_submitted_as_facility_resource_responses(self):
        response = self.client.post(
            self.questionnaire_url("submit-resource"),
            {
                "resource_id": str(self.facility.external_id),
                "results": self.answers(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("referral", str(response.data).lower())
        self.assert_no_submissions()

    def test_referral_forms_cannot_create_patient_or_encounter_drafts(self):
        for with_encounter in (False, True):
            with self.subTest(with_encounter=with_encounter):
                payload = {
                    "questionnaire": str(self.questionnaire.external_id),
                    "patient": str(self.patient.external_id),
                    "status": "draft",
                    "response_dump": {"results": self.answers()},
                }
                if with_encounter:
                    payload["encounter"] = str(self.encounter.external_id)
                response = self.client.post(
                    reverse("form_submission-list"), payload, format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("referral", str(response.data).lower())
                self.assert_no_submissions()
