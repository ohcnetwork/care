from unittest.mock import patch
from uuid import uuid4

from django.core.cache.backends.locmem import LocMemCache
from django.urls import reverse

from care.emr.locks.questionnaire import QuestionnaireLock
from care.emr.models.action import Action
from care.emr.models.questionnaire import Questionnaire
from care.utils.tests.base import CareAPITestBase


class ActionConfigurationAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        action_cache = patch(
            "care.emr.models.action.cache", LocMemCache(str(uuid4()), {})
        )
        action_cache.start()
        self.addCleanup(action_cache.stop)
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.client.force_authenticate(self.user)
        self.payload = {
            "name": "Notify patient",
            "description": "Patient notification",
            "action_context": "PATIENT",
            "performable": True,
            "actions": [
                {
                    "condition": "True",
                    "instructions": [
                        {
                            "slug": "show_message",
                            "context": "self",
                            "params": {"message": "Welcome"},
                        }
                    ],
                }
            ],
        }

    def create_action(self, **kwargs):
        return Action.objects.create(**(self.payload | kwargs))

    def detail_url(self, action):
        return reverse(
            "action-configuration-detail", kwargs={"external_id": action.external_id}
        )

    def test_superuser_can_create_retrieve_update_and_delete_instance_actions(self):
        response = self.client.post(
            reverse("action-configuration-list"), self.payload, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        action = Action.objects.get(external_id=response.data["id"])
        self.assertEqual(action.created_by, self.user)
        self.assertEqual(action.actions, self.payload["actions"])
        detail = self.client.get(self.detail_url(action))
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["name"], self.payload["name"])
        updated = self.client.put(
            self.detail_url(action), {"name": "Updated notification"}, format="json"
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        action.refresh_from_db()
        self.assertEqual(action.name, "Updated notification")
        self.assertEqual(action.actions, self.payload["actions"])
        deleted = self.client.delete(self.detail_url(action))
        self.assertEqual(deleted.status_code, 204, deleted.data)
        self.assertFalse(Action.objects.filter(pk=action.pk).exists())

    def test_regular_users_cannot_create_update_or_delete_actions(self):
        action = self.create_action()
        self.client.force_authenticate(self.create_user())
        for method, url, payload in (
            ("post", reverse("action-configuration-list"), self.payload),
            ("put", self.detail_url(action), {"name": "Unauthorized edit"}),
            ("delete", self.detail_url(action), {}),
        ):
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, payload, format="json")
                self.assertEqual(response.status_code, 403, response.data)
        action.refresh_from_db()
        self.assertEqual(action.name, self.payload["name"])
        self.assertEqual(Action.objects.count(), 1)

    def test_facility_actions_cannot_be_managed_through_instance_api(self):
        response = self.client.post(
            reverse("action-configuration-list"),
            self.payload | {"facility": str(self.facility.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        action = self.create_action(facility=self.facility)
        for method, payload in (("put", {"name": "Edited"}), ("delete", {})):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.detail_url(action), payload, format="json"
                )
                self.assertEqual(response.status_code, 403, response.data)

    def test_creation_validates_context_and_name(self):
        for values in ({"action_context": "UNKNOWN"}, {"name": "x" * 255}):
            with self.subTest(values=values):
                response = self.client.post(
                    reverse("action-configuration-list"),
                    self.payload | values,
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Action.objects.exists())

    def test_catalogues_include_registered_contexts_fields_and_instruction_schemas(
        self,
    ):
        contexts = self.client.get(reverse("action-configuration-contexts"))
        self.assertEqual(contexts.status_code, 200, contexts.data)
        self.assertIn("PatientQuestionnaire", contexts.data["contexts"])
        fields = self.client.get(reverse("action-configuration-fields"))
        self.assertEqual(fields.status_code, 200, fields.data)
        self.assertIn(
            {"context_type": "Patient", "field": "name", "evaluation": "static"},
            fields.data["fields"],
        )
        instructions = self.client.get(reverse("action-configuration-instructions"))
        self.assertEqual(instructions.status_code, 200, instructions.data)
        schemas = {item["slug"]: item for item in instructions.data["instructions"]}
        self.assertEqual(schemas["show_message"]["instruction_type"], "NOTIFY")
        self.assertIn("message", schemas["show_message"]["input_schema"]["properties"])
        self.assertIn(
            "priority", schemas["set_encounter_priority"]["input_schema"]["properties"]
        )
        self.assertIn("tag_patient", schemas)
        self.assertIn("tag_encounter", schemas)

    def test_instance_and_facility_action_lookup_are_scoped_and_cache_is_invalidated(
        self,
    ):
        instance = self.create_action()
        facility_action = self.create_action(
            name="Facility notification", facility=self.facility, actions=[]
        )
        other_facility = self.create_facility(user=self.user)
        self.create_action(name="Other facility", facility=other_facility, actions=[{}])
        self.create_action(
            name="Other context", action_context="APPOINTMENT", actions=[{}]
        )
        self.assertEqual(
            Action.get_actions_for_context("PATIENT", self.facility),
            [instance.actions, facility_action.actions],
        )
        instance.actions = [self.payload["actions"][0] | {"condition": "False"}]
        instance.save(update_fields=["actions"])
        facility_action.actions = [self.payload["actions"][0]]
        facility_action.save(update_fields=["actions"])
        self.assertEqual(
            Action.get_actions_for_context("PATIENT", self.facility),
            [instance.actions, facility_action.actions],
        )

    def test_authenticated_user_is_required(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse("action-configuration-list"))
        self.assertEqual(response.status_code, 403, response.data)

    def test_questionnaire_revisions_preserve_actions_when_omitted_from_update(self):
        question = {
            "id": str(uuid4()),
            "link_id": "reason",
            "text": "Reason for appointment",
            "type": "text",
        }
        created = self.client.post(
            reverse("questionnaire-list"),
            {
                "title": "Appointment assessment",
                "slug": "action-assessment",
                "status": "active",
                "subject_type": "patient",
                "auth_context": "instance",
                "questions": [question],
                "actions": self.payload["actions"],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200, created.data)
        questionnaire = Questionnaire.objects.get(external_id=created.data["id"])
        with (
            patch.object(QuestionnaireLock, "acquire"),
            patch.object(QuestionnaireLock, "release"),
        ):
            updated = self.client.put(
                reverse(
                    "questionnaire-detail",
                    kwargs={"external_id": questionnaire.external_id},
                ),
                {
                    "title": "Updated assessment",
                    "status": "active",
                    "questions": [question | {"text": "Updated reason"}],
                },
                format="json",
            )
        self.assertEqual(updated.status_code, 200, updated.data)
        questionnaire.refresh_from_db()
        previous = Questionnaire.objects.get(latest_revision=questionnaire)
        self.assertEqual(questionnaire.internal_revision, 2)
        self.assertEqual(previous.internal_revision, 1)
        self.assertEqual(previous.questions[0]["text"], question["text"])
        self.assertEqual(questionnaire.questions[0]["text"], "Updated reason")
        self.assertEqual(questionnaire.actions, self.payload["actions"])
        self.assertEqual(previous.actions, self.payload["actions"])

    def test_questionnaire_creation_rejects_unknown_instructions_and_invalid_priority(
        self,
    ):
        for instruction in (
            {"slug": "missing", "context": "self", "params": {}},
            {
                "slug": "set_encounter_priority",
                "context": "self",
                "params": {"priority": "invalid"},
            },
        ):
            with self.subTest(instruction=instruction):
                response = self.client.post(
                    reverse("questionnaire-list"),
                    {
                        "title": "Invalid action assessment",
                        "slug": "invalid-action-assessment",
                        "status": "active",
                        "subject_type": "patient",
                        "auth_context": "instance",
                        "questions": [],
                        "actions": [
                            {"condition": "True", "instructions": [instruction]}
                        ],
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Questionnaire.objects.exists())
