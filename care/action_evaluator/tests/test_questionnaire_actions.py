import uuid

from django.urls import reverse

from care.emr.models import Encounter, Patient
from care.emr.models.tag_config import TagConfig
from care.utils.tests.base import CareAPITestBase


class QuestionnaireActionsTestBase(CareAPITestBase):
    """An encounter questionnaire with one boolean question, submitted for a
    patient/encounter pair — the fixture every action test builds on."""

    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient(gender="male")
        self.encounter = self.create_encounter(
            self.patient, self.facility, self.facility_organization, priority="routine"
        )
        self.client.force_authenticate(user=self.user)
        self.fever_id = str(uuid.uuid4())

    def questions(self):
        return [
            {
                "id": self.fever_id,
                "link_id": "fever",
                "text": "Fever?",
                "type": "boolean",
            }
        ]

    def create_questionnaire(self, actions, subject_type="encounter"):
        payload = {
            "title": "Actions",
            "slug": f"actions-{uuid.uuid4().hex[:8]}",
            "version": "1.0",
            "status": "active",
            "subject_type": subject_type,
            "auth_context": "instance",
            "questions": self.questions(),
            "actions": actions,
        }
        return self.client.post(reverse("questionnaire-list"), payload, format="json")

    def submit(self, questionnaire_id, fever):
        url = reverse("questionnaire-submit", kwargs={"external_id": questionnaire_id})
        body = {
            "resource_id": str(self.encounter.external_id),
            "patient": str(self.patient.external_id),
            "encounter": str(self.encounter.external_id),
            "results": [
                {"question_id": self.fever_id, "values": [{"value": str(fever)}]}
            ],
        }
        return self.client.post(url, body, format="json")

    def create_tag(self, resource, facility=None, display="Urgent"):
        return TagConfig.objects.create(
            status="active",
            display=display,
            category="clinical",
            priority=1,
            resource=resource,
            facility=facility,
        )


class ActionRegistryTests(QuestionnaireActionsTestBase):
    def test_registry_serves_the_catalog(self):
        instructions = self.client.get(reverse("action-configuration-instructions"))
        self.assertEqual(instructions.status_code, 200)
        slugs = {entry["slug"] for entry in instructions.json()["instructions"]}
        self.assertTrue(
            {"show_message", "set_encounter_priority", "tag_encounter", "tag_patient"}
            <= slugs
        )
        tag = next(
            entry
            for entry in instructions.json()["instructions"]
            if entry["slug"] == "tag_encounter"
        )
        self.assertEqual(
            tag["input_schema"]["properties"]["tag"]["x-care-picker"], "tag_config"
        )

        fields = self.client.get(reverse("action-configuration-fields"))
        self.assertEqual(fields.status_code, 200)
        pairs = {
            (entry["context_type"], entry["field"]) for entry in fields.json()["fields"]
        }
        self.assertTrue(
            {
                ("PatientQuestionnaire", "patient"),
                ("EncounterQuestionnaire", "encounter"),
                ("Patient", "gender"),
                ("Patient", "date_of_birth"),
                ("Encounter", "status"),
                ("Encounter", "priority"),
            }
            <= pairs
        )


class ShowMessageTests(QuestionnaireActionsTestBase):
    def test_message_can_splice_answers_and_patient_fields(self):
        response = self.create_questionnaire(
            [
                {
                    "condition": "q_fever == True",
                    "instructions": [
                        {
                            "slug": "show_message",
                            "params": {
                                "message": "{{ f\"Fever: {q_fever}, patient {patient['gender']}\" }}"
                            },
                            "context": "self",
                        }
                    ],
                }
            ]
        )
        self.assertEqual(response.status_code, 200, response.json())
        submitted = self.submit(response.json()["id"], fever=True)
        self.assertEqual(submitted.status_code, 200, submitted.json())
        self.assertEqual(
            submitted.json()["_actions"],
            [
                {
                    "slug": "show_message",
                    "instruction_type": "NOTIFY",
                    "results": {"message": "Fever: True, patient male"},
                }
            ],
        )

    def test_condition_on_encounter_and_patient_context(self):
        response = self.create_questionnaire(
            [
                {
                    "condition": 'encounter["status"] == "in_progress" and patient["gender"] == "male" and patient["deceased"] == False',
                    "instructions": [
                        {
                            "slug": "show_message",
                            "params": {"message": "context ok"},
                            "context": "self",
                        }
                    ],
                },
                {
                    "condition": 'encounter["priority"] == "stat"',
                    "instructions": [
                        {
                            "slug": "show_message",
                            "params": {"message": "never"},
                            "context": "self",
                        }
                    ],
                },
            ]
        )
        self.assertEqual(response.status_code, 200, response.json())
        submitted = self.submit(response.json()["id"], fever=False)
        self.assertEqual(submitted.status_code, 200, submitted.json())
        self.assertEqual(
            [entry["results"]["message"] for entry in submitted.json()["_actions"]],
            ["context ok"],
        )


class SetEncounterPriorityTests(QuestionnaireActionsTestBase):
    def action(self, priority):
        return {
            "condition": "q_fever == True",
            "instructions": [
                {
                    "slug": "set_encounter_priority",
                    "params": {"priority": priority},
                    "context": "encounter",
                }
            ],
        }

    def test_sets_priority_only_when_the_condition_holds(self):
        response = self.create_questionnaire([self.action("stat")])
        self.assertEqual(response.status_code, 200, response.json())
        questionnaire_id = response.json()["id"]

        unchanged = self.submit(questionnaire_id, fever=False)
        self.assertEqual(unchanged.status_code, 200, unchanged.json())
        self.assertEqual(unchanged.json()["_actions"], [])
        self.assertEqual(
            Encounter.objects.get(id=self.encounter.id).priority, "routine"
        )

        escalated = self.submit(questionnaire_id, fever=True)
        self.assertEqual(escalated.status_code, 200, escalated.json())
        outcome = escalated.json()["_actions"][0]
        self.assertEqual(outcome["instruction_type"], "PERFORMED")
        self.assertTrue(outcome["results"]["performed"])
        self.assertEqual(Encounter.objects.get(id=self.encounter.id).priority, "stat")

        # A second run is a no-op that says so instead of failing.
        again = self.submit(questionnaire_id, fever=True)
        self.assertEqual(again.status_code, 200, again.json())
        self.assertFalse(again.json()["_actions"][0]["results"]["performed"])

    def test_save_rejects_an_unknown_priority(self):
        response = self.create_questionnaire([self.action("nope")])
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown encounter priority", str(response.json()))


class TagInstructionTests(QuestionnaireActionsTestBase):
    def test_tags_encounter_and_patient_once(self):
        encounter_tag = self.create_tag("encounter", facility=self.facility)
        patient_tag = self.create_tag("patient", display="Follow up")
        response = self.create_questionnaire(
            [
                {
                    "condition": "True",
                    "instructions": [
                        {
                            "slug": "tag_encounter",
                            "params": {"tag": str(encounter_tag.external_id)},
                            "context": "encounter",
                        },
                        {
                            "slug": "tag_patient",
                            "params": {"tag": str(patient_tag.external_id)},
                            "context": "patient",
                        },
                    ],
                }
            ]
        )
        self.assertEqual(response.status_code, 200, response.json())
        submitted = self.submit(response.json()["id"], fever=True)
        self.assertEqual(submitted.status_code, 200, submitted.json())
        results = [entry["results"] for entry in submitted.json()["_actions"]]
        self.assertTrue(all(result["performed"] for result in results), results)
        self.assertIn(
            encounter_tag.id, Encounter.objects.get(id=self.encounter.id).tags
        )
        self.assertIn(
            patient_tag.id, Patient.objects.get(id=self.patient.id).instance_tags
        )

        again = self.submit(response.json()["id"], fever=True)
        self.assertEqual(again.status_code, 200, again.json())
        results = [entry["results"] for entry in again.json()["_actions"]]
        self.assertEqual([result["performed"] for result in results], [False, False])
        self.assertIn("already set", results[0]["message"])

    def test_save_rejects_a_tag_of_the_wrong_resource(self):
        patient_tag = self.create_tag("patient")
        response = self.create_questionnaire(
            [
                {
                    "condition": "True",
                    "instructions": [
                        {
                            "slug": "tag_encounter",
                            "params": {"tag": str(patient_tag.external_id)},
                            "context": "encounter",
                        }
                    ],
                }
            ]
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not a encounter tag", str(response.json()))

    def test_save_rejects_a_missing_tag(self):
        response = self.create_questionnaire(
            [
                {
                    "condition": "True",
                    "instructions": [
                        {"slug": "tag_patient", "params": {}, "context": "patient"}
                    ],
                }
            ]
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("A tag is required", str(response.json()))
