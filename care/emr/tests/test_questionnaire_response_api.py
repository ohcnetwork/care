import uuid
from datetime import timedelta

from django.conf import settings
from django.urls import reverse

from care.emr.models.questionnaire import QuestionnaireResponse
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class QuestionnaireTestBase(CareAPITestBase):
    """
    This class handles the initial setup of test data including users, organizations, and patients,
    as well as providing utility methods for questionnaire submission and validation.
    """

    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.organization = self.create_organization(org_type="govt")
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )

        self.questionnaire_url = reverse("questionnaire-list")
        self.client.force_authenticate(user=self.user)
        self.questionnaire = self._create_questionnaire(questions=self.questions)
        self.questionnaire_response = self._submit(self.responses)
        self.permissions = [
            PatientPermissions.can_view_questionnaire_responses.name,
            PatientPermissions.can_view_clinical_data.name,
            EncounterPermissions.can_read_encounter_clinical_data.name,
            EncounterPermissions.can_submit_encounter_questionnaire.name,
        ]
        self.role = self.create_role_with_permissions(permissions=self.permissions)

    def get_url(self):
        return reverse(
            "questionnaire-response-list",
            kwargs={
                "patient_external_id": self.patient.external_id,
            },
        )

    def get_detail_url(self, questionnaire_external_id):
        return reverse(
            "questionnaire-response-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": questionnaire_external_id,
            },
        )

    questions = [
        {
            "id": "31f02e46-7d14-4a68-9c94-de009b54fb54",
            "text": "Bilateral Air Entry",
            "type": "group",
            "link_id": "1.1",
            "required": False,
            "questions": [
                {
                    "id": "9358475e-b6f3-4a59-a88d-4b4e66222879",
                    "text": "Is bilateral air entry present?",
                    "type": "choice",
                    "link_id": "1.1.1",
                    "required": True,
                    "answer_option": [{"value": "yes"}, {"value": "no"}],
                },
                {
                    "id": "63631f8f-0880-4758-891b-8ad7ac663be8",
                    "text": "Note on Bilateral Air Entry",
                    "type": "text",
                    "link_id": "1.1.2",
                    "required": False,
                },
            ],
        },
        {
            "id": "80130e9a-e15c-4181-a32e-73dc68bd8755",
            "text": "Respiratory Support",
            "type": "group",
            "link_id": "1.2",
            "required": True,
            "questions": [
                {
                    "id": "56634d0c-5321-41ff-8f0e-a6a4525be6ff",
                    "text": "Select Modality",
                    "type": "choice",
                    "link_id": "1.2.1",
                    "required": True,
                    "answer_option": [
                        {"value": "oxygen_support"},
                        {"value": "non_invasive"},
                        {"value": "invasive"},
                    ],
                },
                {
                    "id": "d9bd1fa1-38ba-48ca-afdd-b0ff0623568e",
                    "text": "Select Oxygen Support Device",
                    "type": "choice",
                    "link_id": "1.2.2",
                    "required": False,
                    "answer_option": [
                        {"value": "nasal_prongs"},
                        {"value": "simple_face_mask"},
                        {"value": "nrm"},
                        {"value": "hfnc"},
                    ],
                },
                {
                    "id": "0493d006-af74-42c3-bb4a-c03ee735b05d",
                    "text": "Oxygen Flow Rate (L/min)",
                    "type": "decimal",
                    "link_id": "1.2.3",
                    "required": False,
                },
                {
                    "id": "54a458e2-4ea0-4f0e-ad1c-c7e8cf9c0a12",
                    "text": "Select Ventilator Mode (Non-invasive)",
                    "type": "choice",
                    "link_id": "1.2.4",
                    "required": False,
                    "answer_option": [
                        {"value": "cmv"},
                        {"value": "simv"},
                        {"value": "cpap_psv"},
                    ],
                },
            ],
            "styling_metadata": {"containerClasses": "grid-2-col"},
        },
        {
            "id": "c0f9e113-57e5-4167-a326-f86c6b457b62",
            "text": "Ventilation Parameters",
            "type": "group",
            "link_id": "1.3",
            "required": False,
            "questions": [
                {
                    "id": "8fdaf3ab-3fa2-475e-a605-b05654f22ec7",
                    "text": "PEEP (cm H2O)",
                    "type": "decimal",
                    "link_id": "1.3.1",
                    "required": False,
                },
                {
                    "id": "9b922018-5468-418e-a205-e3c1f9bb6847",
                    "text": "PIP (cm H2O)",
                    "type": "decimal",
                    "link_id": "1.3.2",
                    "required": False,
                },
                {
                    "id": "e5661139-58b2-4773-96a8-cf9ec51e0320",
                    "text": "MAP (cm H2O)",
                    "type": "decimal",
                    "link_id": "1.3.3",
                    "required": False,
                },
                {
                    "id": "65d21913-c59a-4b4d-99ea-3411b0fcdce1",
                    "text": "Ventilator RR (breaths per minute)",
                    "type": "integer",
                    "link_id": "1.3.4",
                    "required": False,
                },
                {
                    "id": "0e5391e3-a6b3-44ab-8f20-9050aa279680",
                    "text": "Pressure Support (cm H2O)",
                    "type": "decimal",
                    "link_id": "1.3.5",
                    "required": False,
                },
                {
                    "id": "46c70bd9-7dd8-47d9-80d3-4de7fc4d77c4",
                    "text": "Tidal Volume (mL)",
                    "type": "integer",
                    "link_id": "1.3.6",
                    "required": False,
                },
                {
                    "id": "286afbde-9ac1-4717-964e-17453fa0ea01",
                    "text": "FiO2 (%)",
                    "type": "decimal",
                    "link_id": "1.3.7",
                    "required": False,
                },
            ],
            "styling_metadata": {"containerClasses": "grid-2-col"},
        },
    ]

    responses = [
        # Bilateral Air Entry group
        {
            "question_id": "9358475e-b6f3-4a59-a88d-4b4e66222879",  # Is bilateral air entry present?
            "values": [{"value": "yes"}],
        },
        {
            "question_id": "63631f8f-0880-4758-891b-8ad7ac663be8",  # Note on Bilateral Air Entry
            "values": [{"value": "Clear"}],
        },
        # Respiratory Support group
        {
            "question_id": "56634d0c-5321-41ff-8f0e-a6a4525be6ff",  # Select Modality
            "values": [{"value": "oxygen_support"}],
        },
        {
            "question_id": "d9bd1fa1-38ba-48ca-afdd-b0ff0623568e",  # Select Oxygen Support Device
            "values": [{"value": "nasal_prongs"}],
        },
        {
            "question_id": "0493d006-af74-42c3-bb4a-c03ee735b05d",  # Oxygen Flow Rate (L/min)
            "values": [{"value": "2.5"}],
        },
        {
            "question_id": "54a458e2-4ea0-4f0e-ad1c-c7e8cf9c0a12",  # Select Ventilator Mode (Non-invasive)
            "values": [{"value": "cmv"}],
        },
        # Ventilation Parameters group
        {
            "question_id": "8fdaf3ab-3fa2-475e-a605-b05654f22ec7",  # PEEP (cm H2O)
            "values": [{"value": "5"}],
        },
        {
            "question_id": "9b922018-5468-418e-a205-e3c1f9bb6847",  # PIP (cm H2O)
            "values": [{"value": "15"}],
        },
        {
            "question_id": "e5661139-58b2-4773-96a8-cf9ec51e0320",  # MAP (cm H2O)
            "values": [{"value": "10"}],
        },
        {
            "question_id": "65d21913-c59a-4b4d-99ea-3411b0fcdce1",  # Ventilator RR (breaths per minute)
            "values": [{"value": "20"}],
        },
        {
            "question_id": "0e5391e3-a6b3-44ab-8f20-9050aa279680",  # Pressure Support (cm H2O)
            "values": [{"value": "8"}],
        },
        {
            "question_id": "46c70bd9-7dd8-47d9-80d3-4de7fc4d77c4",  # Tidal Volume (mL)
            "values": [{"value": "450"}],
        },
        {
            "question_id": "286afbde-9ac1-4717-964e-17453fa0ea01",  # FiO2 (%)
            "values": [{"value": "40"}],
        },
    ]

    def _submit_questionnaire(self, payload):
        """
        Submits a questionnaire response and returns the submission results.

        Args:
            payload (dict): The questionnaire submission data containing answers

        Returns:
            tuple: A pair of (status_code, response_data) from the submission
        """
        submit_url = reverse(
            "questionnaire-submit", kwargs={"slug": self.questionnaire["slug"]}
        )
        response = self.client.post(submit_url, payload, format="json")
        return response.json()

    def _submit(self, responses):
        """
        Utility method to submit responses.
        Returns a tuple: (status_code, response_data)
        """
        payload = {
            "resource_id": str(self.encounter.external_id),
            "encounter": str(self.encounter.external_id),
            "patient": str(self.patient.external_id),
            "results": responses,
        }
        return self._submit_questionnaire(payload)

    def _create_questionnaire(self, questions, **kwargs):
        """
        Creates a test questionnaire containing all supported question types.

        Returns:
            dict: The created questionnaire data with various question types and validation rules
        """

        questionnaire_definition = {
            "title": kwargs.get("title", "Respiratory Status Assessment"),
            "slug": kwargs.get("slug", "respiratory_status-v3"),
            "description": kwargs.get(
                "description",
                "A form to document respiratory status, including bilateral air entry and respiratory support details.",
            ),
            "status": kwargs.get("status", "active"),
            "subject_type": kwargs.get("subject_type", "encounter"),
            "organizations": [str(self.organization.external_id)],
            "questions": questions,
        }

        response = self.client.post(
            self.questionnaire_url, questionnaire_definition, format="json"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Questionnaire creation failed: {response.json()}",
        )
        return response.json()

    # Testcases for retrive questionnaire responses

    def test_retrieve_questionnaire_response(self):
        """
        Tests retrieval of a submitted questionnaire response and validates the response data structure and content.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.role,
        )
        response = self.client.get(
            self.get_detail_url(self.questionnaire_response["id"])
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["id"], self.questionnaire_response["id"])
        self.assertEqual(response_data["status"], "completed")
        self.assertEqual(response_data["questionnaire"]["id"], self.questionnaire["id"])
        self.assertEqual(len(response_data["responses"]), len(self.responses))

    def test_retrieve_questionnaire_response_without_encounter_permission(self):
        """
        Tests that retrieving a questionnaire response without appropriate permissions results in a permission denied error.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(
            self.get_detail_url(self.questionnaire_response["id"]),
            {"encounter": self.encounter.external_id},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to view questionnaire responses",
        )

    def test_retrieve_questionnaire_response_without_patient_permission(self):
        """
        Tests that retrieving a questionnaire response without appropriate patient permissions results in a permission denied error.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(
            self.get_detail_url(self.questionnaire_response["id"])
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to view questionnaire responses",
        )

    def test_retrieve_questionnaire_response_with_questionnaire_slug_filter(self):
        """
        Tests retrieval of questionnaire responses filtered by questionnaire slug and validates the response data.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.role,
        )
        response = self.client.get(
            self.get_url(), {"questionnaire_slugs": self.questionnaire["slug"]}
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["results"]), 1)
        self.assertEqual(
            response_data["results"][0]["id"], self.questionnaire_response["id"]
        )

    def test_retrieve_questionnaire_response_with_only_unstructured_filter(self):
        """
        Tests retrieval of questionnaire responses filtered by only unstructured responses and validates the response data.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.role,
        )
        response = self.client.get(self.get_url(), {"only_unstructured": "true"})
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["results"]), 1)
        self.assertEqual(
            response_data["results"][0]["id"], self.questionnaire_response["id"]
        )

    # Test cases for listing questionnaire responses

    def test_list_questionnaire_responses_as_superuser(self):
        """
        Tests listing of questionnaire responses for a patient and validates the response data structure and content.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.role,
        )
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["results"]), 1)
        self.assertEqual(
            response_data["results"][0]["id"], self.questionnaire_response["id"]
        )

    def test_list_questionnaire_responses_without_encounter_permission(self):
        """
        Tests that listing questionnaire responses without appropriate permissions results in a permission denied error.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(
            self.get_url(), {"encounter": self.encounter.external_id}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to view questionnaire responses",
        )

    def test_list_questionnaire_responses_without_patient_permission(self):
        """
        Tests that listing questionnaire responses without appropriate patient permissions results in a permission denied error.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to view questionnaire responses",
        )

    def test_list_questionnaire_responses_with_invalid_encounter_uuid(self):
        """
        Tests that listing questionnaire responses with an invalid encounter UUID results in a not found error.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.role,
        )
        response = self.client.get(self.get_url(), {"encounter": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["errors"][0]["msg"],
            "No Encounter matches the given query.",
        )

    def test_list_questionnaire_responses_with_invalid_patient_uuid(self):
        """
        Tests that listing questionnaire responses with an invalid patient UUID results in a not found error.
        """
        self.attach_role_facility_organization_user(
            self.facility_organization,
            self.user,
            self.role,
        )
        url = reverse(
            "questionnaire-response-list",
            kwargs={
                "patient_external_id": str(uuid.uuid4()),
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["errors"][0]["msg"],
            "No Patient matches the given query.",
        )

    #  Test cases for udpdate the questionnaire response

    def test_update_questionnaire_response_status_as_superuser(self):
        """
        Tests updating the status of a questionnaire response and validates the update results.
        """

        update_url = self.get_detail_url(self.questionnaire_response["id"])
        response = self.client.patch(
            update_url, {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["id"], self.questionnaire_response["id"])
        self.assertEqual(response_data["status"], "entered_in_error")

    def test_update_questionnaire_response_status_without_permission(self):
        """
        Tests that updating the status of a questionnaire response without appropriate permissions results in a permission denied error.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        update_url = self.get_detail_url(self.questionnaire_response["id"])
        response = self.client.put(
            update_url, {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to view questionnaire responses",
        )

    def test_update_questionnaire_response_status_already_entered_in_error(self):
        """
        Tests that updating the status of a questionnaire response that is already entered in error results in a permission denied error.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        self.attach_role_facility_organization_user(
            self.facility_organization,
            user,
            self.role,
        )
        update_url = self.get_detail_url(self.questionnaire_response["id"])
        response = self.client.put(
            update_url, {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.put(update_url, {"status": "completed"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Questionnaire Response cannot be edited",
        )

    def test_update_questionnaire_response_status_after_time_limit(self):
        """
        Tests that updating the status of a questionnaire response after the allowed time limit results in a permission denied error.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        self.attach_role_facility_organization_user(
            self.facility_organization,
            user,
            self.role,
        )
        update_url = self.get_detail_url(self.questionnaire_response["id"])
        response = self.client.put(
            update_url, {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        # Simulate time passing beyond the allowed limit
        questionnaire_response_obj = QuestionnaireResponse.objects.get(
            external_id=self.questionnaire_response["id"]
        )
        questionnaire_response_obj.created_date -= timedelta(
            minutes=settings.QUESTIONNAIRE_ERRORED_TIME_LIMIT_MINUTES + 1
        )
        questionnaire_response_obj.save()
        # Ensure the object is refreshed from DB to avoid stale data
        questionnaire_response_obj.refresh_from_db()
        response = self.client.put(update_url, {"status": "completed"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Questionnaire Response cannot be edited",
        )
