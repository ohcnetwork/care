from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.emr.reports.context_builder.data_points.questionnaire import (
    QuestionnaireContextBuilder,
)
from care.utils.tests.base import CareAPITestBase


class QuestionnaireReportContextTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(self.user)
        self.organization = self.create_facility_organization(self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            self.patient, self.facility, self.organization
        )
        self.question = {
            "id": str(uuid4()),
            "link_id": "temperature",
            "text": "Current temperature label",
            "type": "decimal",
        }
        self.questionnaire = Questionnaire.objects.create(
            slug="temperature",
            title="Current assessment",
            description="Current description",
            subject_type="encounter",
            status="active",
            internal_revision=2,
            questions=[self.question],
        )

    def response(self, **kwargs):
        return QuestionnaireResponse.objects.create(
            **{
                "patient": self.patient,
                "encounter": self.encounter,
                "subject_id": self.patient.external_id,
                "questionnaire": self.questionnaire,
                "revision": self.questionnaire.internal_revision,
                "status": "completed",
                **kwargs,
            }
        )

    def test_report_uses_metadata_and_questions_from_the_submitted_revision(self):
        original_question = self.question | {"text": "Original temperature label"}
        Questionnaire.objects.create(
            latest_revision=self.questionnaire,
            slug=self.questionnaire.slug,
            title="Original assessment",
            description="Original description",
            subject_type="encounter",
            status="active",
            internal_revision=1,
            questions=[original_question],
        )
        answer = {"question_id": self.question["id"], "values": [{"value": "37.5"}]}
        response = self.response(revision=1, responses=[answer])

        context = QuestionnaireContextBuilder(context=response)

        self.assertEqual(context.title, "Original assessment")
        self.assertEqual(context.description, "Original description")
        rendered = list(context.responses)
        self.assertEqual(len(rendered), 1)
        self.assertEqual(rendered[0].question, original_question)
        self.assertEqual(rendered[0].answer, answer)

    def test_report_includes_only_completed_questionnaire_responses_for_the_encounter(
        self,
    ):
        included = self.response()
        self.response(status="entered_in_error")
        self.response(questionnaire=None, structured_responses={"procedure": {}})
        other_encounter = self.create_encounter(
            self.patient, self.facility, self.organization
        )
        self.response(encounter=other_encounter)

        context = QuestionnaireContextBuilder(parent_context=self.encounter)

        self.assertEqual([row.context.pk for row in context], [included.pk])

    def test_current_revision_metadata_is_loaded_with_the_response_queryset(self):
        self.response()
        self.response()
        context = QuestionnaireContextBuilder(parent_context=self.encounter)

        with self.assertNumQueries(1):
            metadata = [(row.title, row.description) for row in context]

        self.assertEqual(
            metadata,
            [("Current assessment", "Current description")] * 2,
        )

    def test_slug_filter_returns_latest_responses_first_and_respects_limit(self):
        older = self.response()
        latest = self.response()
        QuestionnaireResponse.objects.filter(pk=older.pk).update(
            created_date=timezone.now() - timedelta(days=1)
        )
        other = Questionnaire.objects.create(
            slug="other-form", title="Other", subject_type="encounter", status="active"
        )
        self.response(questionnaire=other)
        context = QuestionnaireContextBuilder(parent_context=self.encounter)

        self.assertEqual(
            [row.context.pk for row in context.filter(slug="temperature")],
            [latest.pk, older.pk],
        )
        self.assertEqual(
            [row.context.pk for row in context.filter(slug="temperature", limit=1)],
            [latest.pk],
        )

    def test_filter_requires_a_questionnaire_slug(self):
        context = QuestionnaireContextBuilder(parent_context=self.encounter)
        with self.assertRaisesRegex(ValueError, "slug is required"):
            context.filter()
