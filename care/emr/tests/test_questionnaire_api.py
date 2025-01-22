import uuid

from django.urls import reverse
from model_bakery import baker

from care.security.permissions.questionnaire import QuestionnairePermissions
from care.utils.tests.base import CareAPITestBase


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
                self.assertIn(f"Invalid {question_type}", error["msg"])


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

        response = self.client.post(
            self.base_url, self._create_questionnaire(), format="json"
        )
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

    def test_active_questionnaire_modification_prevented(self):
        """
        Verifies that active questionnaires with submitted responses cannot be modified.
        Tests the business rule that prevents modification of questionnaires that are
        already in use to maintain data integrity.
        """
        # Create and submit a response to make the questionnaire active
        questionnaire = self.create_questionnaire_instance()
        self.questionnaire_data = questionnaire
        detail_url = reverse(
            "questionnaire-detail", kwargs={"slug": questionnaire["slug"]}
        )
        self.client.force_authenticate(user=self.super_user)

        # Submit a response to activate the questionnaire
        question = questionnaire["questions"][0]
        submission_payload = self._create_submission_payload(question["id"], None)
        self._submit_questionnaire(submission_payload)

        # Attempt to modify the active questionnaire
        updated_data = self._create_questionnaire()
        updated_data["questions"] = [
            {"link_id": "1", "type": "boolean", "text": "Modified question text"}
        ]

        response = self.client.put(detail_url, updated_data, format="json")
        response_data = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response_data)
        error = response_data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Cannot edit an active questionnaire", error["msg"])

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
