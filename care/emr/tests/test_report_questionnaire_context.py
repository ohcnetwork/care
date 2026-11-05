from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from care.emr.reports.context_builder.data_points.questionnaire import (
    QuestionnaireContextBuilder,
)


class ReportQuestionnaireContextTests(SimpleTestCase):
    def setUp(self):
        self.questionnaires = self.enterContext(
            patch("care.emr.models.questionnaire.Questionnaire.objects")
        )
        self.questionnaires.get.side_effect = AssertionError(
            "Report filters must not look up questionnaires globally"
        )
        self.responses = self.enterContext(
            patch("care.emr.models.questionnaire.QuestionnaireResponse.objects")
        )
        self.scoped_qs = Mock(spec=["filter"])
        self.filtered_qs = Mock(spec=["order_by"])
        self.results = MagicMock(spec=["__iter__"])
        self.scoped_qs.filter.return_value = self.filtered_qs
        self.filtered_qs.order_by.return_value = self.results
        self.builder = QuestionnaireContextBuilder(context=self.scoped_qs)

    def test_missing_questionnaire_returns_empty_responses_without_global_lookup(self):
        self.results.__iter__.return_value = iter([])

        self.assertEqual(list(self.builder.filter(slug="unconfigured-specialty")), [])

        self.scoped_qs.filter.assert_called_once_with(
            questionnaire__slug="unconfigured-specialty"
        )
        self.filtered_qs.order_by.assert_called_once_with("-created_date")
        self.assertEqual(self.questionnaires.mock_calls, [])
        self.assertEqual(self.responses.mock_calls, [])

    def test_existing_questionnaire_filters_only_the_provided_scope(self):
        response = SimpleNamespace(
            questionnaire=SimpleNamespace(title="Encounter form")
        )
        self.results.__iter__.return_value = iter([response])

        rows = list(self.builder.filter(slug="existing-specialty"))

        self.assertEqual([row.title for row in rows], ["Encounter form"])
        self.assertIs(rows[0].context, response)
        self.scoped_qs.filter.assert_called_once_with(
            questionnaire__slug="existing-specialty"
        )
        self.filtered_qs.order_by.assert_called_once_with("-created_date")
        self.assertEqual(self.questionnaires.mock_calls, [])
        self.assertEqual(self.responses.mock_calls, [])

    def test_slug_remains_required_without_querying(self):
        with self.assertRaisesMessage(ValueError, "slug is required"):
            list(self.builder.filter())

        self.scoped_qs.filter.assert_not_called()
        self.filtered_qs.order_by.assert_not_called()
        self.assertEqual(self.questionnaires.mock_calls, [])
        self.assertEqual(self.responses.mock_calls, [])
