from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase
from pydantic import ValidationError as PydanticValidationError
from rest_framework.exceptions import ValidationError

from care.action_evaluator.base import ActionEvaluator, Instruction
from care.action_evaluator.context_engine.contexts.core import (
    EncounterContext,
    PatientContext,
)
from care.action_evaluator.context_engine.evaluator import ActionContextEvaluator
from care.action_evaluator.instruction_engine.instructions.set_encounter_priority import (
    SetEncounterPriorityInstruction,
)
from care.action_evaluator.instruction_engine.instructions.tag_resource import (
    TagEncounterInstruction,
    TagPatientInstruction,
)
from care.action_evaluator.instruction_engine.resolvers import (
    resolve_encounter,
    resolve_patient,
)
from care.action_evaluator.utils import get_all_variables
from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.models.tag_config import TagConfig
from care.emr.resources.encounter.constants import EncounterPriorityChoices
from care.utils.tests.base import CareAPITestBase


class ActionEvaluatorTests(SimpleTestCase):
    def evaluator(self, actions, **kwargs):
        patient = Patient(name="Example Patient", gender="female")
        return ActionEvaluator(None, None, "Patient", patient, actions, **kwargs)

    def message_action(self, condition, message="Condition met"):
        return {
            "condition": condition,
            "instructions": [
                {
                    "slug": "show_message",
                    "context": "self",
                    "params": {"message": message},
                }
            ],
        }

    def test_variable_extraction_preserves_paths_and_ignores_function_names(self):
        self.assertEqual(
            get_all_variables(
                "len(patient['name']) > threshold and patient.gender == 'female'"
            ),
            {"patient.name", "patient.gender", "threshold"},
        )

    def test_false_and_empty_conditions_do_not_run_instructions(self):
        evaluator = self.evaluator(
            [self.message_action("False"), self.message_action("")]
        )
        self.assertEqual(evaluator.evaluate(), [])

    def test_conditions_resolve_patient_fields_and_interpolate_expressions(self):
        evaluator = self.evaluator(
            [self.message_action("gender == 'female'", "{{'Hello ' + name}}")]
        )
        self.assertEqual(
            evaluator.evaluate(),
            [
                {
                    "slug": "show_message",
                    "instruction_type": "NOTIFY",
                    "results": {"message": "Hello Example Patient"},
                }
            ],
        )

    def test_questionnaire_answer_cache_can_drive_conditions_and_messages(self):
        evaluator = self.evaluator(
            [self.message_action("q_temperature > 38", "{{q_temperature * 2}}")],
            field_cache={"q_temperature": 39},
        )
        self.assertEqual(evaluator.evaluate()[0]["results"], {"message": "78"})

    def test_instruction_outputs_follow_action_order(self):
        evaluator = self.evaluator(
            [
                self.message_action("True", "First"),
                self.message_action("True", "Second"),
            ]
        )
        self.assertEqual(
            [result["results"]["message"] for result in evaluator.evaluate()],
            ["First", "Second"],
        )

    def test_unsafe_expressions_are_rejected(self):
        with self.assertRaises(ValueError):
            self.evaluator([]).evaluate_condition("(1).__class__")

    def test_unknown_fields_and_instructions_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError, "No context value found"):
            self.evaluator([]).evaluate_condition("missing_field == 1")
        action = self.message_action("True")
        action["instructions"][0]["slug"] = "does_not_exist"
        with self.assertRaisesRegex(ValueError, "Instruction does_not_exist not found"):
            self.evaluator([action]).evaluate()
        with self.assertRaisesRegex(ValidationError, "not found"):
            ActionEvaluator.authorize(None, None, action)

    def test_internal_instruction_slugs_are_reserved(self):
        with self.assertRaises(PydanticValidationError):
            Instruction(slug="i_internal", params={}, context="self")

    def test_priority_authorization_rejects_unknown_values(self):
        for priority in (None, "unknown-priority"):
            with self.subTest(priority=priority), self.assertRaises(ValidationError):
                SetEncounterPriorityInstruction.authorize(
                    None, None, {"priority": priority}
                )
        self.assertTrue(
            SetEncounterPriorityInstruction.authorize(
                None, None, {"priority": "urgent"}
            )
        )

    def test_nested_questionnaire_context_resolves_patient_fields(self):
        patient = Patient(name="Example Patient", date_of_birth=date(2000, 1, 2))
        fields = {}
        contexts = {}
        evaluator = ActionContextEvaluator(None, None, fields, contexts, {})
        response = SimpleNamespace(patient=patient)
        self.assertEqual(
            evaluator.evaluate(
                "patient.date_of_birth", "PatientQuestionnaire", response
            ),
            "2000-01-02",
        )
        self.assertEqual(fields["patient.date_of_birth"], "2000-01-02")
        self.assertIsInstance(
            evaluator.evaluate(
                "patient", "PatientQuestionnaire", response, context_mode=True
            ),
            PatientContext,
        )

    def test_cached_fields_are_reused(self):
        evaluator = ActionContextEvaluator(None, None, {"name": "Cached"}, {}, {})
        self.assertEqual(evaluator.evaluate("name", "Patient", Patient()), "Cached")

    def test_resolvers_accept_models_wrappers_and_questionnaire_responses(self):
        patient = Patient()
        encounter = Encounter()
        for context in (
            patient,
            PatientContext(patient),
            SimpleNamespace(patient=patient),
        ):
            with self.subTest(context=context):
                self.assertIs(resolve_patient(context), patient)
        for context in (
            encounter,
            EncounterContext(encounter),
            SimpleNamespace(encounter=encounter),
        ):
            with self.subTest(context=context):
                self.assertIs(resolve_encounter(context), encounter)
        self.assertIsNone(resolve_patient(SimpleNamespace(patient="invalid")))
        self.assertIsNone(resolve_encounter(SimpleNamespace(encounter=None)))


class ActionInstructionPersistenceTests(CareAPITestBase):
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
            priority=EncounterPriorityChoices.routine.value,
        )

    def instruction(self, instruction_class, context, params):
        return instruction_class(None, self.user, context, params, {}, {})

    def test_priority_instruction_updates_the_encounter_and_is_idempotent(self):
        instruction = self.instruction(
            SetEncounterPriorityInstruction,
            EncounterContext(self.encounter),
            {"priority": "urgent"},
        )
        self.assertTrue(instruction.evaluate()["performed"])
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.priority, "urgent")
        with self.assertNumQueries(0):
            self.assertFalse(instruction.evaluate()["performed"])

    def test_priority_instruction_handles_a_form_without_encounter(self):
        result = self.instruction(
            SetEncounterPriorityInstruction,
            SimpleNamespace(encounter=None),
            {"priority": "urgent"},
        ).evaluate()
        self.assertFalse(result["performed"])
        self.assertIsNone(result["priority"])
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.priority, "routine")

    def test_missing_tags_are_reported_without_changing_the_resource(self):
        result = self.instruction(
            TagEncounterInstruction, self.encounter, {"tag": str(uuid4())}
        ).evaluate()
        self.assertFalse(result["performed"])
        self.assertEqual(result["message"], "Tag no longer exists")

    def test_tag_authorization_validates_presence_resource_and_permission(self):
        tag = TagConfig.objects.create(
            display="Follow up", resource="encounter", facility=self.facility
        )
        for params in ({}, {"tag": str(uuid4())}):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                TagEncounterInstruction.authorize(None, self.user, params)
        with self.assertRaisesRegex(ValidationError, "not a patient tag"):
            TagPatientInstruction.authorize(None, self.user, {"tag": tag.external_id})
        user = self.create_user()
        with self.assertRaisesRegex(ValidationError, "not allowed"):
            TagEncounterInstruction.authorize(None, user, {"tag": tag.external_id})
        self.assertTrue(
            TagEncounterInstruction.authorize(None, self.user, {"tag": tag.external_id})
        )

    def test_encounter_tag_instruction_applies_the_tag(self):
        tag = TagConfig.objects.create(
            display="Follow up", resource="encounter", facility=self.facility
        )
        result = self.instruction(
            TagEncounterInstruction,
            EncounterContext(self.encounter),
            {"tag": str(tag.external_id)},
        ).evaluate()
        self.assertTrue(result["performed"], result)
        self.encounter.refresh_from_db()
        self.assertIn(tag.id, self.encounter.tags)

    def test_tag_instruction_reports_permission_errors(self):
        tag = TagConfig.objects.create(
            display="Follow up", resource="encounter", facility=self.facility
        )
        instruction = self.instruction(
            TagEncounterInstruction, self.encounter, {"tag": str(tag.external_id)}
        )
        instruction.user = self.create_user()
        result = instruction.evaluate()
        self.assertFalse(result["performed"])
        self.encounter.refresh_from_db()
        self.assertNotIn(tag.id, self.encounter.tags)

    def test_tag_instruction_handles_a_form_without_a_target(self):
        tag = TagConfig.objects.create(
            display="Follow up", resource="patient", facility=self.facility
        )
        result = self.instruction(
            TagPatientInstruction,
            SimpleNamespace(patient=None),
            {"tag": str(tag.external_id)},
        ).evaluate()
        self.assertFalse(result["performed"])
        self.assertIn("Nothing to tag", result["message"])
