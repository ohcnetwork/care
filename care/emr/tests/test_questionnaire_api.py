import uuid

from django.conf import settings
from django.urls import reverse
from model_bakery import baker

from care.emr.models.observation import Observation
from care.emr.resources.questionnaire.spec import QuestionType
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.utils.tests.base import CareAPITestBase


def deterministic_uuid(string):
    """
    Generates a UUID based on the provided string.

    Args:
        string (str): The input string to generate a UUID from.

    Returns:
        str: A UUID generated from the input string.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, string))


class QuestionnaireTestBase(CareAPITestBase):
    """
    Foundation test class that provides common setup and helper methods for testing questionnaire functionality.

    This class handles the initial setup of test data including users, organizations, and patients,
    as well as providing utility methods for questionnaire submission and validation.
    """

    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.organization = self.create_organization(org_type="govt")
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse("questionnaire-list")
        self.questionnaire_data = self._create_questionnaire()
        self.questions = self.questionnaire_data.get("questions", [])

    def _submit_questionnaire(self, payload):
        """
        Submits a questionnaire response and returns the submission results.

        Args:
            payload (dict): The questionnaire submission data containing answers

        Returns:
            tuple: A pair of (status_code, response_data) from the submission
        """
        submit_url = reverse(
            "questionnaire-submit", kwargs={"slug": self.questionnaire_data["slug"]}
        )
        response = self.client.post(submit_url, payload, format="json")
        return response.status_code, response.json()

    def _get_question_by_type(self, question_type):
        """
        Retrieves a question from the questionnaire based on its type.

        Args:
            question_type (str): The type of question to find (e.g., 'boolean', 'text')

        Returns:
            dict: The first question matching the specified type
        """
        return next(q for q in self.questions if q["type"] == question_type)

    def _create_submission_payload(self, question_id, answer_value):
        """
        Creates a standardized submission payload for questionnaire testing.

        Args:
            question_id (str): The ID of the question being answered
            answer_value: The value to submit as the answer

        Returns:
            dict: A properly formatted submission payload
        """
        return {
            "resource_id": str(self.patient.external_id),
            "patient": str(self.patient.external_id),
            "results": [
                {"question_id": question_id, "values": [{"value": answer_value}]}
            ],
        }

    def create_questionnaire_tag(self, **kwargs):
        from care.emr.models import QuestionnaireTag

        return baker.make(QuestionnaireTag, **kwargs)


class QuestionnaireValidationTests(QuestionnaireTestBase):
    """
    Comprehensive test suite for validating questionnaire submissions across all supported question types.

    Tests both valid and invalid submissions to ensure proper validation handling and error reporting.
    Covers all question types including boolean, numeric, text, date/time, and choice-based questions.
    """

    def _create_questionnaire(self):
        """
        Creates a test questionnaire containing all supported question types.

        Returns:
            dict: The created questionnaire data with various question types and validation rules
        """
        question_templates = {
            "base": {
                "code": {
                    "display": "Test Value",
                    "system": "http://test_system.care/test",
                    "code": "123",
                }
            },
            "choice": {
                "answer_option": [
                    {"value": "EXCELLENT", "display": "Excellent"},
                    {"value": "GOOD", "display": "Good"},
                    {"value": "FAIR", "display": "Fair"},
                    {"value": "POOR", "display": "Poor"},
                ]
            },
        }

        questions = [
            {"link_id": "1", "type": "boolean", "text": "Current symptom presence"},
            {"link_id": "2", "type": "decimal", "text": "Current body temperature"},
            {"link_id": "3", "type": "integer", "text": "Duration of symptoms (days)"},
            {"link_id": "4", "type": "string", "text": "Patient full name"},
            {"link_id": "5", "type": "text", "text": "Detailed symptom description"},
            {"link_id": "6", "type": "display", "text": "Completion acknowledgment"},
            {"link_id": "7", "type": "date", "text": "Initial symptom date"},
            {"link_id": "8", "type": "dateTime", "text": "Symptom onset timestamp"},
            {"link_id": "9", "type": "time", "text": "Latest medication time"},
            {"link_id": "10", "type": "url", "text": "Medical history URL"},
            {"link_id": "11", "type": "structured", "text": "Structured medical data"},
            {
                "link_id": "12",
                "type": "choice",
                "text": "Overall health assessment",
                **question_templates["choice"],
            },
        ]

        for question in questions:
            question.update(question_templates["base"])

        questionnaire_definition = {
            "title": "Comprehensive Health Assessment",
            "slug": "ques-multi-type",
            "description": "Complete health assessment questionnaire with various response types",
            "status": "active",
            "subject_type": "patient",
            "organizations": [str(self.organization.external_id)],
            "questions": questions,
            "tags": [self.create_questionnaire_tag().external_id],
        }

        response = self.client.post(
            self.base_url, questionnaire_definition, format="json"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Questionnaire creation failed: {response.json()}",
        )
        return response.json()

    def _get_valid_test_value(self, question_type):
        """
        Provides valid test values for each supported question type.

        Args:
            question_type (str): The type of question requiring a test value

        Returns:
            str: A valid value for the specified question type
        """
        valid_values = {
            "boolean": "true",
            "decimal": "37.5",
            "integer": "7",
            "string": "Jane Smith",
            "text": "Persistent cough with fever",
            "date": "2023-12-31",
            "dateTime": "2023-12-31T15:30:00",
            "time": "15:30:00",
            "choice": "EXCELLENT",
            "url": "http://example.com",
            "structured": "Structured Medical Data",
        }
        return valid_values.get(question_type)

    def _get_invalid_test_value(self, question_type):
        """
        Provides invalid test values for each supported question type.

        Args:
            question_type (str): The type of question requiring an invalid test value

        Returns:
            str: An invalid value for the specified question type
        """
        invalid_values = {
            "boolean": "invalid_boolean",
            "decimal": "not_a_number",
            "integer": "12.34",
            "date": "invalid-date",
            "dateTime": "01-16-2025T10:30:00",
            "time": "25:61:00",
            "choice": "INVALID_CHOICE",
            "url": "not_a_url",
            "text": "a" * settings.MAX_QUESTIONNAIRE_TEXT_RESPONSE_SIZE + "extra",
        }
        return invalid_values.get(question_type)

    def test_complete_valid_submission(self):
        """
        Verifies that a questionnaire submission with valid values for all question types is accepted.
        """
        results = []
        for question in self.questions:
            if question["type"] != "display":
                value = self._get_valid_test_value(question["type"])
                if value:
                    results.append(
                        {"question_id": question["id"], "values": [{"value": value}]}
                    )

        payload = {
            "resource_id": str(self.patient.external_id),
            "patient": str(self.patient.external_id),
            "results": results,
        }

        status_code, response_data = self._submit_questionnaire(payload)
        self.assertEqual(status_code, 200, f"Valid submission failed: {response_data}")

    def test_individual_invalid_submissions(self):
        """
        Tests validation handling for invalid submissions of each question type.
        Ensures appropriate error messages are returned for each type of invalid input.
        """
        test_types = [
            "boolean",
            "decimal",
            "integer",
            "date",
            "dateTime",
            "time",
            "choice",
            "url",
            "text",
        ]

        for question_type in test_types:
            question = self._get_question_by_type(question_type)
            invalid_value = self._get_invalid_test_value(question_type)

            payload = self._create_submission_payload(question["id"], invalid_value)
            status_code, response_data = self._submit_questionnaire(payload)

            with self.subTest(question_type=question_type):
                self.assertEqual(status_code, 400)
                self.assertIn("errors", response_data)
                error = response_data["errors"][0]
                self.assertEqual(error["type"], "type_error")
                self.assertEqual(error["question_id"], question["id"])
                if question_type == QuestionType.text.value:
                    self.assertIn(
                        f"Text too long. Max allowed size is {settings.MAX_QUESTIONNAIRE_TEXT_RESPONSE_SIZE}",
                        error["msg"],
                    )
                else:
                    self.assertIn(f"Invalid {question_type}", error["msg"])

    def test_submit_inactive_questionnaire(self):
        """
        Tests that submitting a response to an inactive questionnaire returns a 400 error.
        """
        questionnaire_definition = {
            "title": "Inactive Questionnaire",
            "slug": "inactive-ques",
            "description": "This questionnaire is inactive.",
            "status": "draft",
            "subject_type": "patient",
            "organizations": [str(self.organization.external_id)],
            "questions": [
                {
                    "link_id": "1",
                    "type": "boolean",
                    "text": "Is this active?",
                },
            ],
        }
        response = self.client.post(
            self.base_url, questionnaire_definition, format="json"
        )
        self.assertEqual(response.status_code, 200)

        submit_url = reverse(
            "questionnaire-submit", kwargs={"slug": response.json()["slug"]}
        )

        payload = {
            "resource_id": str(self.patient.external_id),
            "patient": str(self.patient.external_id),
            "results": [{"question_id": uuid.uuid4(), "values": [{"value": ""}]}],
        }
        response = self.client.post(submit_url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())
        error = response.json()["errors"][0]
        self.assertEqual(error["msg"]["type"], "questionnaire_inactive")

    def test_false_choice_values_validations(self):
        questionnaire_definition = {
            "title": "Comprehensive Health Assessment",
            "slug": "ques-choices-type",
            "description": "Complete health assessment questionnaire with various response types",
            "status": "active",
            "subject_type": "patient",
            "organizations": [str(self.organization.external_id)],
            "questions": [
                {
                    "link_id": "1",
                    "type": "choice",
                    "text": "Overall health assessment",
                    "answer_option": [
                        {"value": " ", "display": "Excellent"},
                        {"value": "GOOD", "display": "Good"},
                        {"value": "FAIR", "display": "Fair"},
                        {"value": "POOR", "display": "Poor"},
                    ],
                },
            ],
        }
        response = self.client.post(
            self.base_url, questionnaire_definition, format="json"
        )
        data = response.json()
        status_code = response.status_code
        self.assertEqual(status_code, 400)
        self.assertIn("errors", data)
        error = data["errors"][0]
        self.assertEqual(error["type"], "value_error")
        self.assertIn(
            "All the answer option values must be provided for custom choices",
            error["msg"],
        )


class QuestionnaireEnableWhenSubmissionTests(QuestionnaireTestBase):
    def setUp(self):
        # Override setUp so that we don't create a default questionnaire.
        self.user = self.create_super_user()
        self.organization = self.create_organization(org_type="govt")
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)
        self.base_url = reverse("questionnaire-list")

    def _create_questionnaire(self, questions):
        """
        Creates a questionnaire with the given list of questions.
        A base code template is added to each question and a unique slug is generated.
        """
        question_templates = {
            "base": {
                "code": {
                    "display": "Test Value",
                    "system": "http://test_system.care/test",
                    "code": "123",
                }
            },
        }
        for question in questions:
            question.update(question_templates["base"])
        questionnaire_definition = {
            "title": "Test Questionnaire",
            "slug": f"test-ques-{uuid.uuid4()!s}"[:20],
            "description": "Questionnaire for testing enable_when operators",
            "status": "active",
            "subject_type": "patient",
            "organizations": [str(self.organization.external_id)],
            "questions": questions,
        }
        response = self.client.post(
            self.base_url, questionnaire_definition, format="json"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Questionnaire creation failed: {response.json()}",
        )
        return response.json()

    def _submit(self, responses):
        """
        Utility method to submit responses.
        Returns a tuple: (status_code, response_data)
        """
        payload = {
            "resource_id": str(self.patient.external_id),
            "patient": str(self.patient.external_id),
            "results": responses,
        }
        return self._submit_questionnaire(payload)

    # --- Equals operator ---
    def test_equals_operator_valid(self):
        # Q2 is enabled if Q1 equals "true"
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "2",
                "type": "integer",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "true"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "10"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid equals operator submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertIn(
            self.questions[1]["id"], saved_qids, "Q2 should be present (condition met)"
        )

    def test_equals_operator_invalid(self):
        # Q2 should be disabled because Q1 does not equal "true"
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "2",
                "type": "integer",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "false"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "10"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertNotIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be removed since condition failed",
        )

    # --- Not Equals operator ---
    def test_not_equals_operator_valid(self):
        # Q2 is enabled if Q1 not_equals "true"
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "2",
                "type": "integer",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "not_equals", "answer": "true"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "false"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "20"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid not_equals operator submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be present since condition met",
        )

    def test_not_equals_operator_invalid(self):
        # Q2 should be disabled if Q1 equals "true"
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "2",
                "type": "integer",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "not_equals", "answer": "true"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "true"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "20"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertNotIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be removed since condition failed",
        )

    # --- Greater operator ---
    def test_greater_operator_valid(self):
        # Q2 enabled if Q1 (integer) is greater than 8
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "greater", "answer": "8"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "9"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid greater operator submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be present since condition met",
        )

    def test_greater_operator_invalid(self):
        # Q2 should be disabled because Q1 is not greater than 8.
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "greater", "answer": "8"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "7"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertNotIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be removed since condition failed",
        )

    # --- Less operator ---
    def test_less_operator_valid(self):
        # Q2 enabled if Q1 is less than 10
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [{"question": "1", "operator": "less", "answer": "10"}],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "5"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid less operator submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be present since condition met",
        )

    def test_less_operator_invalid(self):
        # Q2 should be disabled because Q1 is not less than 10.
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [{"question": "1", "operator": "less", "answer": "10"}],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "15"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertNotIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be removed since condition failed",
        )

    # --- Greater or Equals operator ---
    def test_greater_or_equals_operator_valid(self):
        # Q2 is enabled if Q1 is greater or equal to 10
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "greater_or_equals", "answer": "10"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "10"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid greater_or_equals operator submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be present since condition met",
        )

    def test_greater_or_equals_operator_invalid(self):
        # Q2 should be disabled because Q1 is less than 10.
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "greater_or_equals", "answer": "10"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "9"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertNotIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be removed since condition failed",
        )

    # --- Less or Equals operator ---
    def test_less_or_equals_operator_valid(self):
        # Q2 is enabled if Q1 is less or equal to 10
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "less_or_equals", "answer": "10"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "10"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid less_or_equals operator submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be present since condition met",
        )

    def test_less_or_equals_operator_invalid(self):
        # Q2 should be disabled because Q1 is greater than 10.
        questions = [
            {"link_id": "1", "type": "integer", "text": "Q1"},
            {
                "link_id": "2",
                "type": "decimal",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "less_or_equals", "answer": "10"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "15"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertNotIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be removed since condition failed",
        )

    # --- Exists operator ---
    def test_exists_operator_valid(self):
        # Q2 is enabled if Q1 has a non-empty value (exists condition)
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "2",
                "type": "string",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "exists", "answer": "true"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "true"}]},
            {
                "question_id": self.questions[1]["id"],
                "values": [{"value": "A valid answer"}],
            },
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid exists operator submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertIn(self.questions[0]["id"], saved_qids, "Q1 should be present")
        self.assertIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be present since condition met",
        )

    def test_exists_operator_invalid(self):
        # Q2 should be disabled because Q1's answer is empty
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "2",
                "type": "string",
                "text": "Q2",
                "enable_when": [
                    {"question": "1", "operator": "exists", "answer": "true"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = [
            {
                "question_id": self.questions[1]["id"],
                "values": [{"value": "A valid answer"}],
            },
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        self.assertNotIn(
            self.questions[1]["id"],
            saved_qids,
            "Q2 should be removed since condition failed",
        )

    # --- Nested dependency chain tests ---
    def test_nested_dependency_chain_valid(self):
        """
        Test a valid nested dependency chain:
          - Q2 is enabled if Q3 equals "true"
          - Q1 is enabled if Q2 is greater than "5"
        Valid responses: Q3 = "true", Q2 = "10", Q1 = "34.5"
        """
        questions = [
            {"link_id": "3", "type": "boolean", "text": "Q3"},
            {
                "link_id": "2",
                "type": "integer",
                "text": "Q2",
                "enable_when": [
                    {"question": "3", "operator": "equals", "answer": "true"}
                ],
            },
            {
                "link_id": "1",
                "type": "decimal",
                "text": "Q1",
                "enable_when": [
                    {"question": "2", "operator": "greater", "answer": "5"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = []
        for q in questionnaire["questions"]:
            if q["link_id"] == "3":
                responses.append(
                    {"question_id": q["id"], "values": [{"value": "true"}]}
                )
            elif q["link_id"] == "2":
                responses.append({"question_id": q["id"], "values": [{"value": "10"}]})
            elif q["link_id"] == "1":
                responses.append(
                    {"question_id": q["id"], "values": [{"value": "34.5"}]}
                )
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid nested dependency chain should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        # Expect all responses to be present.
        expected_qids = {q["id"] for q in questionnaire["questions"]}
        self.assertSetEqual(
            saved_qids, expected_qids, "All valid responses should be present"
        )

    def test_nested_dependency_chain_invalid(self):
        """
        Test an invalid nested dependency chain:
          - Q2 is enabled if Q3 equals "true"
          - Q1 is enabled if Q2 is greater than "5"
        In this case, Q3 is answered as "false", so Q2 (and thus Q1) should be disabled.
        Even if responses for Q2 and Q1 are provided, they should be ignored.
        """
        questions = [
            {"link_id": "3", "type": "boolean", "text": "Q3"},
            {
                "link_id": "2",
                "type": "integer",
                "text": "Q2",
                "enable_when": [
                    {"question": "3", "operator": "equals", "answer": "true"}
                ],
            },
            {
                "link_id": "1",
                "type": "decimal",
                "text": "Q1",
                "enable_when": [
                    {"question": "2", "operator": "greater", "answer": "5"}
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        responses = []
        for q in questionnaire["questions"]:
            if q["link_id"] == "3":
                # Q3 is "false", so condition fails.
                responses.append(
                    {"question_id": q["id"], "values": [{"value": "false"}]}
                )
            elif q["link_id"] == "2":
                responses.append({"question_id": q["id"], "values": [{"value": "10"}]})
            elif q["link_id"] == "1":
                responses.append(
                    {"question_id": q["id"], "values": [{"value": "34.5"}]}
                )
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        # Expect only Q3 to be present because Q3's false value disables Q2 and Q1.
        q3_id = next(q["id"] for q in questionnaire["questions"] if q["link_id"] == "3")
        self.assertSetEqual(
            saved_qids, {q3_id}, "Only the response for Q3 should be present"
        )

    # --- Enable Behavior tests ---
    def test_enable_behavior_all_valid(self):
        # With default "all" behavior, Q3 is enabled if both conditions are met.
        # Q3 enabled if Q1 equals "true" AND Q2 is greater than "8"
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {"link_id": "2", "type": "integer", "text": "Q2"},
            {
                "link_id": "3",
                "type": "decimal",
                "text": "Q3",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"},
                    {"question": "2", "operator": "greater", "answer": "8"},
                ],
            },  # Default enable_behavior is "all"
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        # Valid: Q1 true, Q2 = 9 (9 > 8)
        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "true"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "9"}]},
            {"question_id": self.questions[2]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid enable_behavior (all) submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        expected_qids = {q["id"] for q in questionnaire["questions"]}
        self.assertSetEqual(
            saved_qids, expected_qids, "All responses should be present"
        )

    def test_enable_behavior_all_invalid(self):
        # With "all" behavior, if one condition fails then Q3 is disabled.
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {"link_id": "2", "type": "integer", "text": "Q2"},
            {
                "link_id": "3",
                "type": "decimal",
                "text": "Q3",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"},
                    {"question": "2", "operator": "greater", "answer": "8"},
                ],
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        # Invalid: Q1 true but Q2 = 7 (fails condition) → Q3 disabled.
        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "true"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "7"}]},
            {"question_id": self.questions[2]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        # Expect only Q1 and Q2 are saved; Q3 is filtered out.
        expected_qids = {self.questions[0]["id"], self.questions[1]["id"]}
        self.assertSetEqual(
            saved_qids, expected_qids, "Only Q1 and Q2 responses should be present"
        )

    def test_enable_behavior_any_valid(self):
        # With "any" behavior, Q3 is enabled if at least one condition is met.
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {"link_id": "2", "type": "integer", "text": "Q2"},
            {
                "link_id": "3",
                "type": "decimal",
                "text": "Q3",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"},
                    {"question": "2", "operator": "greater", "answer": "8"},
                ],
                "enable_behavior": "any",
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        # Valid: Q1 false but Q2 = 9 (one condition met) enables Q3.
        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "false"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "9"}]},
            {"question_id": self.questions[2]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Valid enable_behavior (any) submission should succeed: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        expected_qids = {q["id"] for q in questionnaire["questions"]}
        self.assertSetEqual(
            saved_qids, expected_qids, "All responses should be present"
        )

    def test_enable_behavior_any_invalid(self):
        # With "any" behavior, Q3 is disabled only if neither condition is met.
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {"link_id": "2", "type": "integer", "text": "Q2"},
            {
                "link_id": "3",
                "type": "decimal",
                "text": "Q3",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"},
                    {"question": "2", "operator": "greater", "answer": "8"},
                ],
                "enable_behavior": "any",
            },
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        # Invalid: Q1 false AND Q2 = 7 (neither condition met) → Q3 disabled.
        responses = [
            {"question_id": self.questions[0]["id"], "values": [{"value": "false"}]},
            {"question_id": self.questions[1]["id"], "values": [{"value": "7"}]},
            {"question_id": self.questions[2]["id"], "values": [{"value": "34.5"}]},
        ]
        status_code, response_data = self._submit(responses)
        self.assertEqual(
            status_code,
            200,
            f"Submission should succeed in ignore mode: {response_data}",
        )
        saved_qids = {
            resp["question_id"] for resp in response_data.get("responses", [])
        }
        # Expect only Q1 and Q2 are saved; Q3 should be filtered out.
        expected_qids = {self.questions[0]["id"], self.questions[1]["id"]}
        self.assertSetEqual(
            saved_qids, expected_qids, "Only Q1 and Q2 responses should be present"
        )

    def test_nested_group_enable_when_valid(self):
        """
        Valid case:
        - Q1 = true → enables Group G1
        - Q2 (in G1) = true → enables Q3
        - Q3 is submitted → all questions saved
        """
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "grp-1",
                "type": "group",
                "text": "Group G1",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
                "questions": [
                    {"link_id": "2", "type": "boolean", "text": "Q2"},
                    {
                        "link_id": "3",
                        "type": "decimal",
                        "text": "Q3",
                        "enable_when": [
                            {"question": "2", "operator": "equals", "answer": "true"}
                        ],
                    },
                ],
            },
        ]

        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = []

        for q in questionnaire["questions"]:
            if q["type"] == "group":
                self.questions.extend(q["questions"])
            else:
                self.questions.append(q)

        q1 = next(q for q in self.questions if q["link_id"] == "1")
        q2 = next(q for q in self.questions if q["link_id"] == "2")
        q3 = next(q for q in self.questions if q["link_id"] == "3")

        responses = [
            {"question_id": q1["id"], "values": [{"value": "true"}]},
            {"question_id": q2["id"], "values": [{"value": "true"}]},
            {"question_id": q3["id"], "values": [{"value": "42.0"}]},
        ]

        status_code, response_data = self._submit(responses)
        self.assertEqual(status_code, 200)

        saved_qids = {resp["question_id"] for resp in response_data["responses"]}
        self.assertSetEqual(saved_qids, {q1["id"], q2["id"], q3["id"]})

    def test_nested_group_enable_when_invalid(self):
        """
        Invalid case:
        - Q1 = false → disables Group G1
        - Q2 and Q3 are ignored even if submitted
        """
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "grp-1",
                "type": "group",
                "text": "Group G1",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
                "questions": [
                    {"link_id": "2", "type": "boolean", "text": "Q2"},
                    {
                        "link_id": "3",
                        "type": "decimal",
                        "text": "Q3",
                        "enable_when": [
                            {"question": "2", "operator": "equals", "answer": "true"}
                        ],
                    },
                ],
            },
        ]

        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = []

        for q in questionnaire["questions"]:
            if q["type"] == "group":
                self.questions.extend(q["questions"])
            else:
                self.questions.append(q)

        q1 = next(q for q in self.questions if q["link_id"] == "1")
        q2 = next(q for q in self.questions if q["link_id"] == "2")
        q3 = next(q for q in self.questions if q["link_id"] == "3")

        responses = [
            {"question_id": q1["id"], "values": [{"value": "false"}]},  # disables group
            {"question_id": q2["id"], "values": [{"value": "true"}]},
            {"question_id": q3["id"], "values": [{"value": "42.0"}]},
        ]

        status_code, response_data = self._submit(responses)
        self.assertEqual(status_code, 200)

        saved_qids = {resp["question_id"] for resp in response_data["responses"]}
        self.assertSetEqual(saved_qids, {q1["id"]}, "Only Q1 should be saved")

    def test_nested_group_partial_enable_inner_question_invalid(self):
        """
        Case:
        - Q1 = true → enables Group G1
        - Q2 = false → disables Q3
        Expected: Q1 and Q2 are saved, Q3 is ignored
        """
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "grp-1",
                "type": "group",
                "text": "Group G1",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
                "questions": [
                    {"link_id": "2", "type": "boolean", "text": "Q2"},
                    {
                        "link_id": "3",
                        "type": "decimal",
                        "text": "Q3",
                        "enable_when": [
                            {"question": "2", "operator": "equals", "answer": "true"}
                        ],
                    },
                ],
            },
        ]

        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = []

        for q in questionnaire["questions"]:
            if q["type"] == "group":
                self.questions.extend(q["questions"])
            else:
                self.questions.append(q)

        q1 = next(q for q in self.questions if q["link_id"] == "1")
        q2 = next(q for q in self.questions if q["link_id"] == "2")
        q3 = next(q for q in self.questions if q["link_id"] == "3")

        responses = [
            {"question_id": q1["id"], "values": [{"value": "true"}]},  # Enables group
            {
                "question_id": q2["id"],
                "values": [{"value": "false"}],
            },  # Q2 answered false
            {
                "question_id": q3["id"],
                "values": [{"value": "42.0"}],
            },  # Q3 condition fails
        ]

        status_code, response_data = self._submit(responses)
        self.assertEqual(status_code, 200)

        saved_qids = {resp["question_id"] for resp in response_data["responses"]}
        self.assertSetEqual(
            saved_qids,
            {q1["id"], q2["id"]},
            "Q3 should not be saved because Q2 was false",
        )

    def test_deep_nested_group_enable_when_valid(self):
        """
        Valid case:
        - Q1 = true → enables G1
        - Q2 = true → enables G2
        - Q3 = "yes" → enables Q4
        """
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "grp-1",
                "type": "group",
                "text": "Group G1",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
                "questions": [
                    {"link_id": "2", "type": "boolean", "text": "Q2"},
                    {
                        "link_id": "grp-2",
                        "type": "group",
                        "text": "Group G2",
                        "enable_when": [
                            {"question": "2", "operator": "equals", "answer": "true"}
                        ],
                        "questions": [
                            {"link_id": "3", "type": "string", "text": "Q3"},
                            {
                                "link_id": "4",
                                "type": "decimal",
                                "text": "Q4",
                                "enable_when": [
                                    {
                                        "question": "3",
                                        "operator": "equals",
                                        "answer": "yes",
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
        ]

        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        flat_questions = []

        for q in questionnaire["questions"]:
            if q["type"] == "group":
                for sub in q["questions"]:
                    if sub["type"] == "group":
                        flat_questions.extend(sub["questions"])
                    else:
                        flat_questions.append(sub)
            else:
                flat_questions.append(q)

        flat_questions += [
            q for q in questionnaire["questions"] if q["type"] != "group"
        ]

        q1 = next(q for q in flat_questions if q["link_id"] == "1")
        q2 = next(q for q in flat_questions if q["link_id"] == "2")
        q3 = next(q for q in flat_questions if q["link_id"] == "3")
        q4 = next(q for q in flat_questions if q["link_id"] == "4")

        responses = [
            {"question_id": q1["id"], "values": [{"value": "true"}]},
            {"question_id": q2["id"], "values": [{"value": "true"}]},
            {"question_id": q3["id"], "values": [{"value": "yes"}]},
            {"question_id": q4["id"], "values": [{"value": "42.0"}]},
        ]

        status_code, response_data = self._submit(responses)
        self.assertEqual(status_code, 200)

        saved_qids = {resp["question_id"] for resp in response_data["responses"]}
        self.assertSetEqual(saved_qids, {q1["id"], q2["id"], q3["id"], q4["id"]})

    def test_deep_nested_group_enable_when_invalid(self):
        """
        Invalid case:
        - Q1 = true → enables G1
        - Q2 = false → disables G2 and everything inside
        - Q3 and Q4 should be ignored even if submitted
        """
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "grp-1",
                "type": "group",
                "text": "Group G1",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
                "questions": [
                    {"link_id": "2", "type": "boolean", "text": "Q2"},
                    {
                        "link_id": "grp-2",
                        "type": "group",
                        "text": "Group G2",
                        "enable_when": [
                            {"question": "2", "operator": "equals", "answer": "true"}
                        ],
                        "questions": [
                            {"link_id": "3", "type": "string", "text": "Q3"},
                            {
                                "link_id": "4",
                                "type": "decimal",
                                "text": "Q4",
                                "enable_when": [
                                    {
                                        "question": "3",
                                        "operator": "equals",
                                        "answer": "yes",
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
        ]

        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        flat_questions = []

        for q in questionnaire["questions"]:
            if q["type"] == "group":
                for sub in q["questions"]:
                    if sub["type"] == "group":
                        flat_questions.extend(sub["questions"])
                    else:
                        flat_questions.append(sub)
            else:
                flat_questions.append(q)

        flat_questions += [
            q for q in questionnaire["questions"] if q["type"] != "group"
        ]

        q1 = next(q for q in flat_questions if q["link_id"] == "1")
        q2 = next(q for q in flat_questions if q["link_id"] == "2")
        q3 = next(q for q in flat_questions if q["link_id"] == "3")
        q4 = next(q for q in flat_questions if q["link_id"] == "4")

        responses = [
            {"question_id": q1["id"], "values": [{"value": "true"}]},
            {"question_id": q2["id"], "values": [{"value": "false"}]},  # disables G2
            {"question_id": q3["id"], "values": [{"value": "yes"}]},
            {"question_id": q4["id"], "values": [{"value": "42.0"}]},
        ]

        status_code, response_data = self._submit(responses)
        self.assertEqual(status_code, 200)

        saved_qids = {resp["question_id"] for resp in response_data["responses"]}
        self.assertSetEqual(
            saved_qids, {q1["id"], q2["id"]}, "Q3 and Q4 should not be saved"
        )

    def test_remove_nested_groups_recursively_when_parent_group_disabled(self):
        """
        Q1 = false → disables G1
        G1 contains nested group G2
        G2 contains Q2 and Q3
        We submit answers for Q2 and Q3 → all must be removed
        """
        questions = [
            {"link_id": "1", "type": "boolean", "text": "Q1"},
            {
                "link_id": "grp-1",
                "type": "group",
                "text": "Group G1",
                "enable_when": [
                    {"question": "1", "operator": "equals", "answer": "true"}
                ],
                "questions": [
                    {
                        "link_id": "grp-2",
                        "type": "group",
                        "text": "Group G2",
                        "questions": [
                            {"link_id": "2", "type": "boolean", "text": "Q2"},
                            {"link_id": "3", "type": "decimal", "text": "Q3"},
                        ],
                    }
                ],
            },
        ]

        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        flat = []

        for q in questionnaire["questions"]:
            if q["type"] == "group":
                for sub in q["questions"]:
                    if sub["type"] == "group":
                        flat.extend(sub["questions"])
                    else:
                        flat.append(sub)
            else:
                flat.append(q)

        flat += [q for q in questionnaire["questions"] if q["type"] != "group"]

        q1 = next(q for q in flat if q["link_id"] == "1")
        q2 = next(q for q in flat if q["link_id"] == "2")
        q3 = next(q for q in flat if q["link_id"] == "3")

        responses = [
            {"question_id": q1["id"], "values": [{"value": "false"}]},  # disables G1
            {"question_id": q2["id"], "values": [{"value": "true"}]},
            {"question_id": q3["id"], "values": [{"value": "45.6"}]},
        ]

        status_code, response_data = self._submit(responses)
        self.assertEqual(status_code, 200)

        saved_qids = {resp["question_id"] for resp in response_data["responses"]}
        self.assertSetEqual(
            saved_qids, {q1["id"]}, "Q2 and Q3 inside nested group should be removed"
        )


class RequiredFieldValidationTests(QuestionnaireTestBase):
    """
    Test suite focusing on validation of required fields in questionnaires.

    Ensures that questionnaires properly enforce required field constraints
    and provide appropriate error messages for missing required values.
    """

    def _create_questionnaire(self):
        """
        Creates a questionnaire with mandatory fields for testing required field validation.

        Returns:
            dict: Questionnaire definition with required fields
        """
        questionnaire_definition = {
            "title": "Required Fields Assessment",
            "slug": "mandatory-fields-test",
            "description": "Questionnaire testing required field validation",
            "status": "active",
            "subject_type": "patient",
            "organizations": [str(self.organization.external_id)],
            "tags": [self.create_questionnaire_tag().external_id],
            "questions": [
                {
                    "link_id": "1",
                    "type": "boolean",
                    "text": "Mandatory response field",
                    "required": True,
                    "code": {
                        "display": "Test Value",
                        "system": "http://test_system.care/test",
                        "code": "123",
                    },
                }
            ],
        }

        response = self.client.post(
            self.base_url, questionnaire_definition, format="json"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Questionnaire creation failed: {response.json()}",
        )
        return response.json()

    def test_missing_required_field_submission(self):
        """
        Verifies that submitting a questionnaire without required field values returns appropriate errors.
        """
        question = self.questions[0]
        payload = self._create_submission_payload(question["id"], None)
        payload["results"][0]["values"] = []

        status_code, response_data = self._submit_questionnaire(payload)

        self.assertEqual(status_code, 400)
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "values_missing")
        self.assertEqual(error["question_id"], question["id"])
        self.assertIn("No value provided for question", error["msg"])


class RepeatableGroupsValidationTests(QuestionnaireTestBase):
    """
    Test suite for validating question groups in questionnaires.

    Ensures that questionnaires repeating groups are correctly validated.
    Observation components are also validated to ensure they are correctly created.
    """

    def setUp(self):
        self.user = self.create_super_user()
        self.organization = self.create_organization(org_type="govt")
        self.facility = self.create_facility(self.user)
        self.facility_organization = self.create_facility_organization(self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse("questionnaire-list")
        self.default_code = {
            "display": "Test Value",
            "system": "http://test_system.care/test",
            "code": "123",
        }

    def _create_questionnaire(self, questions=None):
        """
        Creates a questionnaire with the given list of questions.
        A base code template is added to each question and a unique slug is generated.
        """
        questionnaire_definition = {
            "title": "Test Questionnaire",
            "slug": f"test-repeat-ques-{uuid.uuid4()!s}"[:20],
            "description": "Questionnaire for testing repeatable groups",
            "status": "active",
            "subject_type": "encounter",
            "organizations": [str(self.organization.external_id)],
            "questions": questions,
        }
        response = self.client.post(
            self.base_url, questionnaire_definition, format="json"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Questionnaire creation failed: {response.json()}",
        )
        return response.json()

    def _create_submission_payload(self, results):
        """
        Creates a standardized submission payload for questionnaire testing.

        Args:
            question_id (str): The ID of the question being answered
            answer_value: The value to submit as the answer

        Returns:
            dict: A properly formatted submission payload
        """
        return {
            "resource_id": str(self.encounter.external_id),
            "patient": str(self.patient.external_id),
            "encounter": str(self.encounter.external_id),
            "results": results,
        }

    def test_repeatable_group_responses(self):
        """
        Tests the validation of repeatable question groups in a questionnaire.
        """
        questions = [
            {
                "link_id": "1",
                "id": deterministic_uuid("1"),
                "type": "group",
                "text": "Repeatable Group",
                "code": self.default_code,
                "repeats": True,
                "is_component": True,
                "questions": [
                    {
                        "link_id": "1.1",
                        "id": deterministic_uuid("1.1"),
                        "type": "boolean",
                        "text": "Within normal range",
                        "code": {
                            "display": "Test Value Child",
                            "system": "http://test_system.care/test",
                            "code": "123-child",
                        },
                    },
                    {
                        "link_id": "1.2",
                        "id": deterministic_uuid("1.2"),
                        "type": "decimal",
                        "text": "Measurement",
                        "code": {
                            "display": "Test Value Child",
                            "system": "http://test_system.care/test",
                            "code": "124-child",
                        },
                    },
                ],
            }
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        # Test submission with valid data
        payload = self._create_submission_payload(
            [
                {
                    "question_id": deterministic_uuid("1"),
                    "sub_results": [
                        [
                            {
                                "question_id": deterministic_uuid("1.1"),
                                "values": [{"value": "true"}],
                            }
                        ],
                        [
                            {
                                "question_id": deterministic_uuid("1.1"),
                                "values": [{"value": "false"}],
                            },
                            {
                                "question_id": deterministic_uuid("1.2"),
                                "values": [{"value": "34.5"}],
                            },
                        ],
                    ],
                }
            ]
        )
        status_code, response = self._submit_questionnaire(payload)
        self.assertEqual(
            status_code, 200, f"Questionnaire submission failed: {response}"
        )
        observations = Observation.objects.filter(
            questionnaire_response__external_id=response["id"],
        )
        self.assertEqual(observations.count(), 2, "Two observations should be created")
        for observation in observations:
            self.assertEqual(observation.main_code, self.default_code)
            self.assertGreater(
                len(observation.component),
                0,
                "Each observation should have at least one component",
            )

    def test_repeatable_group_responses_validation(self):
        """
        Tests the validation of repeatable question groups in a questionnaire.
        """
        questions = [
            {
                "link_id": "1",
                "id": deterministic_uuid("1"),
                "type": "group",
                "text": "Repeatable Group",
                "code": self.default_code,
                "repeats": True,
                "is_component": True,
                "questions": [
                    {
                        "link_id": "1.1",
                        "id": deterministic_uuid("1.1"),
                        "type": "boolean",
                        "text": "Within normal range",
                        "required": True,
                        "code": {
                            "display": "Test Value Child",
                            "system": "http://test_system.care/test",
                            "code": "123-child",
                        },
                    },
                    {
                        "link_id": "1.2",
                        "id": deterministic_uuid("1.2"),
                        "type": "decimal",
                        "text": "Measurement",
                        "code": {
                            "display": "Test Value Child",
                            "system": "http://test_system.care/test",
                            "code": "124-child",
                        },
                    },
                ],
            }
        ]
        questionnaire = self._create_questionnaire(questions)
        self.questionnaire_data = questionnaire
        self.questions = questionnaire["questions"]

        # Test submission with valid data
        payload = self._create_submission_payload(
            [
                {
                    "question_id": deterministic_uuid("1"),
                    "sub_results": [
                        [
                            {
                                "question_id": deterministic_uuid("1.1"),
                                "values": [{"value": "true"}],
                            }
                        ],
                        [
                            {
                                "question_id": deterministic_uuid("1.2"),
                                "values": [{"value": "34.5"}],
                            },
                        ],
                    ],
                }
            ]
        )
        submit_url = reverse(
            "questionnaire-submit", kwargs={"slug": self.questionnaire_data["slug"]}
        )
        response = self.client.post(submit_url, payload, format="json")
        self.assertEqual(
            response.status_code,
            400,
            f"Questionnaire submission should fail: {response.json()}",
        )
        self.assertContains(response, "Question not answered", status_code=400)


class RequiredGroupValidationTests(QuestionnaireTestBase):
    """
    Test suite for validating required question groups in questionnaires.

    Tests the validation of grouped questions where the entire group
    is marked as required, ensuring proper handling of group-level
    requirements and appropriate error messages.
    """

    def _create_questionnaire(self):
        """
        Creates a questionnaire with required question groups for testing group validation.

        Returns:
            dict: Questionnaire definition with required question groups
        """
        questionnaire_definition = {
            "title": "Required Groups Assessment",
            "slug": "mandatory-groups-test",
            "description": "Questionnaire testing required group validation",
            "status": "active",
            "subject_type": "patient",
            "organizations": [str(self.organization.external_id)],
            "tags": [self.create_questionnaire_tag().external_id],
            "questions": [
                {
                    "styling_metadata": {"layout": "vertical"},
                    "link_id": "grp-1",
                    "type": "group",
                    "text": "Vital Signs Group",
                    "code": {
                        "display": "Test Value",
                        "system": "http://test_system.care/test",
                        "code": "123",
                    },
                    "required": True,
                    "questions": [
                        {
                            "link_id": "1",
                            "type": "boolean",
                            "text": "Within normal range",
                            "code": {
                                "display": "Test Value",
                                "system": "http://test_system.care/test",
                                "code": "123",
                            },
                        }
                    ],
                }
            ],
        }

        response = self.client.post(
            self.base_url, questionnaire_definition, format="json"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Questionnaire creation failed: {response.json()}",
        )

        return response.json()

    def test_missing_required_group_submission(self):
        """
        Verifies that submitting a questionnaire without required group values returns appropriate errors.
        """
        question = self.questions[0]["questions"][0]
        payload = self._create_submission_payload(question["id"], None)
        payload["results"][0]["values"] = []

        status_code, response_data = self._submit_questionnaire(payload)

        self.assertEqual(status_code, 400)
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "values_missing")
        self.assertEqual(error["question_id"], question["id"])
        self.assertIn("No value provided for question", error["msg"])


class QuestionnairePermissionTests(QuestionnaireTestBase):
    """
    Test suite for verifying questionnaire access control and permissions.

    Tests various permission scenarios including read, write, and delete operations
    to ensure proper access control enforcement for different user roles.
    """

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.organization = self.create_organization(org_type="govt")
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)
        self.super_user = self.create_super_user()

    def _create_questionnaire(self):
        """
        Creates a basic questionnaire for testing permission controls.

        Returns:
            dict: Basic questionnaire definition for permission testing
        """
        return {
            "title": "Permission Test Assessment",
            "slug": "permission-test",
            "description": "Questionnaire for testing access controls",
            "status": "active",
            "subject_type": "patient",
            "organizations": [str(self.organization.external_id)],
            "tags": [self.create_questionnaire_tag().external_id],
            "questions": [
                {
                    "link_id": "1",
                    "type": "boolean",
                    "text": "Test question",
                    "required": True,
                    "code": {
                        "display": "Test Value",
                        "system": "http://test_system.care/test",
                        "code": "123",
                    },
                }
            ],
        }

    def create_questionnaire_instance(self):
        """
        Helper method to create a questionnaire instance for testing permissions.
        Temporarily authenticates as super user to ensure creation, then reverts
        to regular user authentication.

        Returns:
            dict: The created questionnaire instance data
        """
        self.client.force_authenticate(self.super_user)
        response = self.client.post(
            self.base_url, self._create_questionnaire(), format="json"
        )
        self.client.force_authenticate(self.user)
        return response.json()

    def test_questionnaire_list_access_denied(self):
        """
        Verifies that users without proper permissions cannot list questionnaires.
        Tests the basic access control for questionnaire listing functionality.
        """
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 403)

    def test_questionnaire_list_access_granted(self):
        """
        Verifies that users with read permissions can successfully list questionnaires.
        Tests proper access grant for users with explicit read permissions.
        """
        permissions = [QuestionnairePermissions.can_read_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_questionnaire_creation_access_denied(self):
        """
        Verifies that users without proper permissions cannot create new questionnaires.
        Tests the write permission enforcement for questionnaire creation.
        """
        response = self.client.post(
            self.base_url, self._create_questionnaire(), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_questionnaire_creation_access_granted(self):
        """
        Verifies that users with write permissions can successfully create questionnaires.
        Tests proper access grant for users with explicit write permissions.
        """
        permissions = [QuestionnairePermissions.can_write_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        questionnaire_data = self._create_questionnaire()
        questionnaire_data["title"] = ""
        response = self.client.post(self.base_url, questionnaire_data, format="json")
        self.assertEqual(response.status_code, 400)

        questionnaire_data["title"] = self.fake.text(max_nb_chars=255)
        response = self.client.post(self.base_url, questionnaire_data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_questionnaire_retrieval_access_denied(self):
        """
        Verifies that users without proper permissions cannot retrieve individual questionnaires.
        Tests access control for detailed questionnaire viewing.
        """
        questionnaire = self.create_questionnaire_instance()
        detail_url = reverse(
            "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 403)

    def test_questionnaire_retrieval_access_granted(self):
        """
        Verifies that users with read permissions can successfully retrieve questionnaires.
        Tests proper access grant for viewing detailed questionnaire information.
        """
        permissions = [QuestionnairePermissions.can_read_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        questionnaire = self.create_questionnaire_instance()
        detail_url = reverse(
            "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

    def test_questionnaire_deletion_access_denied(self):
        """
        Verifies that regular users cannot delete questionnaires even with write permissions.
        Tests that deletion is restricted to super users only.
        """
        # Grant both read and write permissions but verify deletion still fails
        permissions = [
            QuestionnairePermissions.can_write_questionnaire.name,
            QuestionnairePermissions.can_read_questionnaire.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        questionnaire = self.create_questionnaire_instance()
        detail_url = reverse(
            "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
        )
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 403)

    def test_questionnaire_deletion_super_user_allowed(self):
        """
        Verifies that super users can successfully delete questionnaires.
        Tests the highest level of access control for questionnaire management.
        """
        questionnaire = self.create_questionnaire_instance()
        detail_url = reverse(
            "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
        )
        self.client.force_authenticate(user=self.super_user)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)

    def test_questionnaire_update_access_denied(self):
        """
        Verifies that regular users cannot update questionnaires even with basic permissions.
        Tests update restriction enforcement for questionnaire modification.
        """
        permissions = [
            QuestionnairePermissions.can_write_questionnaire.name,
            QuestionnairePermissions.can_read_questionnaire.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        questionnaire = self.create_questionnaire_instance()
        detail_url = reverse(
            "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
        )

        updated_data = self._create_questionnaire()
        updated_data["questions"] = [
            {"link_id": "1", "type": "boolean", "text": "Modified question text"}
        ]

        response = self.client.put(detail_url, updated_data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_questionnaire_update_super_user_allowed(self):
        """
        Verifies that super users can successfully update questionnaires.
        Tests proper update functionality for authorized users and validates
        the applied changes.
        """
        questionnaire = self.create_questionnaire_instance()
        detail_url = reverse(
            "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
        )
        self.client.force_authenticate(user=self.super_user)

        updated_data = self._create_questionnaire()
        updated_data["description"] = ""
        updated_data["questions"] = [
            {
                "link_id": "1",
                "type": "boolean",
                "text": "Modified question text",
                "code": {
                    "display": "Test Value",
                    "system": "http://test_system.care/test",
                    "code": "123",
                },
            }
        ]

        response = self.client.put(detail_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["questions"][0]["text"], "Modified question text"
        )
        self.assertEqual(response.json()["description"], "")

    # def test_active_questionnaire_modification_prevented(self):
    #     """
    #     Verifies that active questionnaires with submitted responses cannot be modified.
    #     Tests the business rule that prevents modification of questionnaires that are
    #     already in use to maintain data integrity.
    #     """
    #     # Create and submit a response to make the questionnaire active
    #     questionnaire = self.create_questionnaire_instance()
    #     self.questionnaire_data = questionnaire
    #     detail_url = reverse(
    #         "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
    #     )
    #     self.client.force_authenticate(user=self.super_user)
    #
    #     # Submit a response to activate the questionnaire
    #     question = questionnaire["questions"][0]
    #     submission_payload = self._create_submission_payload(question["id"], None)
    #     self._submit_questionnaire(submission_payload)
    #
    #     # Attempt to modify the active questionnaire
    #     updated_data = self._create_questionnaire()
    #     updated_data["questions"] = [
    #         {"link_id": "1", "type": "boolean", "text": "Modified question text"}
    #     ]
    #
    #     response = self.client.put(detail_url, updated_data, format="json")
    #     response_data = response.json()
    #
    #     self.assertEqual(response.status_code, 400)
    #     self.assertIn("errors", response_data)
    #     error = response_data["errors"][0]
    #     self.assertEqual(error["type"], "validation_error")
    #     self.assertIn("Cannot edit an active questionnaire", error["msg"])

    def test_questionnaire_organization_list_access_denied(self):
        """
        Verifies that users without proper permissions cannot view the organizations
        associated with a questionnaire.

        """
        questionnaire = self.create_questionnaire_instance()
        organization_list_url = reverse(
            "questionnaire-get-organizations", kwargs={"slug": questionnaire["slug"]}
        )
        response = self.client.get(organization_list_url)
        self.assertEqual(response.status_code, 403)

    def test_questionnaire_organization_list_access_granted(self):
        """
        Verifies that users with read permissions can successfully view the organizations
        associated with a questionnaire.

        """
        permissions = [QuestionnairePermissions.can_read_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        questionnaire = self.create_questionnaire_instance()
        organization_list_url = reverse(
            "questionnaire-get-organizations", kwargs={"slug": questionnaire["slug"]}
        )
        response = self.client.get(organization_list_url)
        self.assertEqual(response.status_code, 200)

    def test_tag_setting_unauthorized_access(self):
        """
        Verifies that users without any permissions cannot set tags on questionnaires.

        """
        questionnaire = self.create_questionnaire_instance()
        tag_url = reverse(
            "questionnaire-set-tags", kwargs={"slug": questionnaire["slug"]}
        )

        payload = {"tags": [self.create_questionnaire_tag().slug]}
        response = self.client.post(tag_url, payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_tag_setting_read_only_access(self):
        """
        Verifies that users with only read permissions cannot set tags on questionnaires.

        """
        questionnaire = self.create_questionnaire_instance()
        tag_url = reverse(
            "questionnaire-set-tags", kwargs={"slug": questionnaire["slug"]}
        )

        permissions = [QuestionnairePermissions.can_read_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        payload = {"tags": [self.create_questionnaire_tag().slug]}
        response = self.client.post(tag_url, payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_tag_setting_invalid_tag_validation(self):
        """
        Verifies that attempts to set non-existent tags are properly validated and rejected.
        """
        questionnaire = self.create_questionnaire_instance()
        tag_url = reverse(
            "questionnaire-set-tags", kwargs={"slug": questionnaire["slug"]}
        )

        permissions = [
            QuestionnairePermissions.can_read_questionnaire.name,
            QuestionnairePermissions.can_write_questionnaire.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        payload = {"tags": ["non-existing-questionnaire-tag-slug"]}
        response = self.client.post(tag_url, payload, format="json")
        self.assertEqual(response.status_code, 404)

    def test_set_tags_for_questionnaire_with_permissions(self):
        permissions = [
            QuestionnairePermissions.can_read_questionnaire.name,
            QuestionnairePermissions.can_write_questionnaire.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        questionnaire = self.create_questionnaire_instance()
        url = reverse("questionnaire-set-tags", kwargs={"slug": questionnaire["slug"]})
        payload = {"tags": [self.create_questionnaire_tag().slug]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

    def test_set_organizations_without_authentication(self):
        """Tests that setting organizations without authentication returns 403 forbidden."""
        questionnaire = self.create_questionnaire_instance()
        url = reverse(
            "questionnaire-set-organizations", kwargs={"slug": questionnaire["slug"]}
        )

        payload = {"organizations": [self.create_organization().external_id]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_set_organizations_with_read_only_access(self):
        """Tests that setting organizations with read-only permissions returns 403 forbidden."""
        questionnaire = self.create_questionnaire_instance()
        url = reverse(
            "questionnaire-set-organizations", kwargs={"slug": questionnaire["slug"]}
        )

        permissions = [QuestionnairePermissions.can_read_questionnaire.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        payload = {"organizations": [self.create_organization().external_id]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_set_organizations_with_invalid_organization_id(self):
        """Tests that setting organizations with non-existent organization ID returns 404 not found."""
        questionnaire = self.create_questionnaire_instance()
        url = reverse(
            "questionnaire-set-organizations", kwargs={"slug": questionnaire["slug"]}
        )

        permissions = [
            QuestionnairePermissions.can_read_questionnaire.name,
            QuestionnairePermissions.can_write_questionnaire.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        payload = {"organizations": [uuid.uuid4()]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 404)

    def test_set_organizations_without_organization_access(self):
        """Tests that setting organizations without access to target organization returns 403 forbidden."""
        questionnaire = self.create_questionnaire_instance()
        url = reverse(
            "questionnaire-set-organizations", kwargs={"slug": questionnaire["slug"]}
        )

        permissions = [
            QuestionnairePermissions.can_read_questionnaire.name,
            QuestionnairePermissions.can_write_questionnaire.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        payload = {"organizations": [self.create_organization().external_id]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_set_organizations_with_valid_access(self):
        """Tests that setting organizations succeeds with proper permissions and organization access."""
        questionnaire = self.create_questionnaire_instance()
        url = reverse(
            "questionnaire-set-organizations", kwargs={"slug": questionnaire["slug"]}
        )

        permissions = [
            QuestionnairePermissions.can_read_questionnaire.name,
            QuestionnairePermissions.can_write_questionnaire.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_organization_user(self.organization, self.user, role)

        payload = {"organizations": [self.organization.external_id]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
