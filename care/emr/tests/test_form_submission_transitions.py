from django.urls import reverse
from model_bakery import baker

from care.emr.models.questionnaire import FormSubmission, Questionnaire
from care.utils.tests.base import CareAPITestBase


class TestFormSubmissionTransitions(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.client.force_authenticate(self.user)
        self.patient = self.create_patient()
        self.questionnaire = baker.make(Questionnaire)

    def make_submission(self, status):
        return baker.make(
            FormSubmission,
            patient=self.patient,
            questionnaire=self.questionnaire,
            status=status,
            response_dump={"answer": "Original"},
        )

    def update(self, submission, status):
        return self.client.put(
            reverse(
                "form_submission-detail",
                kwargs={"external_id": submission.external_id},
            ),
            {"status": status, "response_dump": {"answer": "Revised"}},
            format="json",
        )

    def test_submitted_response_cannot_return_to_draft(self):
        submission = self.make_submission("submitted")
        response = self.update(submission, "draft")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertContains(
            response,
            "Form submission cannot be set to draft after submission",
            status_code=400,
        )
        submission.refresh_from_db()
        self.assertEqual(submission.status, "submitted")
        self.assertEqual(submission.response_dump, {"answer": "Original"})

    def test_entered_in_error_submission_cannot_be_changed(self):
        for status in ("draft", "submitted", "entered_in_error"):
            with self.subTest(status=status):
                submission = self.make_submission("entered_in_error")
                response = self.update(submission, status)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertContains(
                    response,
                    "Form submission is already entered in error",
                    status_code=400,
                )
                submission.refresh_from_db()
                self.assertEqual(submission.status, "entered_in_error")
                self.assertEqual(submission.response_dump, {"answer": "Original"})

    def test_submitted_response_can_be_corrected_or_marked_in_error(self):
        for status in ("submitted", "entered_in_error"):
            with self.subTest(status=status):
                submission = self.make_submission("submitted")
                response = self.update(submission, status)
                self.assertEqual(response.status_code, 200, response.data)
                submission.refresh_from_db()
                self.assertEqual(submission.status, status)
                self.assertEqual(submission.response_dump, {"answer": "Revised"})
                self.assertEqual(submission.updated_by, self.user)

    def test_draft_response_can_be_edited_submitted_or_marked_in_error(self):
        for status in ("draft", "submitted", "entered_in_error"):
            with self.subTest(status=status):
                submission = self.make_submission("draft")
                response = self.update(submission, status)
                self.assertEqual(response.status_code, 200, response.data)
                submission.refresh_from_db()
                self.assertEqual(submission.status, status)
                self.assertEqual(submission.response_dump, {"answer": "Revised"})
