from copy import deepcopy
from uuid import uuid4

from django.test import SimpleTestCase
from django.urls import reverse
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from care.emr.models.facility_resource import (
    FacilityResourceObservation,
    FacilityResourceQuestionnaireResponse,
)
from care.emr.models.observation import Observation
from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.emr.resources.questionnaire.utils import (
    handle_resource_response,
    handle_response,
    validate_questionnaire_response,
)
from care.emr.resources.questionnaire_response.resource_spce import (
    ResourceQuestionnaireSubmitRequest,
)
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseSubmission,
    QuestionnaireSubmitRequest,
    QuestionnaireSubmitResult,
)
from care.utils.tests.base import CareAPITestBase


class QuestionnaireEngineValidationTests(SimpleTestCase):
    def question(self, link_id, question_type="text", **kwargs):
        return {
            "id": str(uuid4()),
            "link_id": link_id,
            "text": link_id,
            "type": question_type,
            **kwargs,
        }

    def answer(self, question, value="Answer", **kwargs):
        return QuestionnaireSubmitResult.model_validate(
            {
                "question_id": question["id"],
                "values": [{"value": value}],
                **kwargs,
            }
        )

    def questionnaire(self, questions, **kwargs):
        return Questionnaire(
            status="active", subject_type="encounter", questions=questions, **kwargs
        )

    def condition(self, controller):
        return {
            "enable_when": [
                {
                    "question": controller["link_id"],
                    "operator": "equals",
                    "answer": True,
                }
            ]
        }

    def test_valid_answers_use_the_shared_cleaned_projection(self):
        text = self.question("reason")
        integer = self.question("count", "integer")
        boolean = self.question("urgent", "boolean")
        decimal = self.question("temperature", "decimal")
        questionnaire = self.questionnaire([text, integer, boolean, decimal])
        result = validate_questionnaire_response(
            questionnaire,
            [
                self.answer(text, "Persistent symptoms"),
                self.answer(integer, "3"),
                self.answer(boolean, "false"),
                self.answer(decimal, "37.5"),
            ],
        )
        self.assertEqual(
            result.cleaned_response,
            {
                "reason": "Persistent symptoms",
                "count": 3,
                "urgent": False,
                "temperature": 37.5,
            },
        )
        self.assertEqual(
            set(result.responses), {q["id"] for q in questionnaire.questions}
        )

    def test_validation_preserves_the_original_questionnaire_and_answers(self):
        child = self.question("reason", required=True)
        group = self.question("assessment", "group", questions=[child])
        questionnaire = self.questionnaire([group])
        answers = [self.answer(child)]
        original_questions = deepcopy(questionnaire.questions)
        original_answers = deepcopy(answers)

        result = validate_questionnaire_response(questionnaire, answers)

        self.assertEqual(questionnaire.questions, original_questions)
        self.assertEqual(answers, original_answers)
        self.assertIsNot(result.questions, questionnaire.questions)
        self.assertIsNot(result.questions[0], questionnaire.questions[0])
        self.assertEqual(result.cleaned_response, {"reason": "Answer"})

    def test_required_answers_cannot_be_omitted_or_empty(self):
        required = self.question("reason", required=True)
        optional = self.question("note")
        questionnaire = self.questionnaire([required, optional])
        for results in (
            [self.answer(optional)],
            [self.answer(optional), self.answer(required, values=[])],
        ):
            with self.subTest(results=results), self.assertRaises(ValidationError):
                validate_questionnaire_response(questionnaire, results)

    def test_invalid_scalar_types_are_rejected(self):
        for question_type in ("integer", "decimal", "boolean", "date"):
            with self.subTest(question_type=question_type):
                question = self.question("value", question_type)
                with self.assertRaises(ValidationError):
                    validate_questionnaire_response(
                        self.questionnaire([question]),
                        [self.answer(question, "invalid")],
                    )

    def test_inactive_and_empty_submissions_keep_the_engine_errors(self):
        question = self.question("reason")
        inactive = self.questionnaire([question])
        inactive.status = "retired"
        with self.assertRaises(ValidationError) as error:
            validate_questionnaire_response(inactive, [self.answer(question)])
        self.assertEqual(error.exception.detail["type"], "questionnaire_inactive")
        with self.assertRaises(ValidationError) as error:
            validate_questionnaire_response(self.questionnaire([question]), [])
        self.assertEqual(error.exception.detail["type"], "questionnaire_empty")

    def test_disabled_required_questions_are_filtered_before_validation(self):
        controller = self.question("urgent", "boolean")
        conditional = self.question(
            "reason", required=True, **self.condition(controller)
        )
        questionnaire = self.questionnaire([controller, conditional])
        result = validate_questionnaire_response(
            questionnaire, [self.answer(controller, "false")]
        )
        self.assertEqual([q["id"] for q in result.questions], [controller["id"]])
        self.assertEqual(result.cleaned_response, {"urgent": False})
        self.assertEqual(len(questionnaire.questions), 2)

    def test_answers_to_disabled_questions_are_rejected(self):
        controller = self.question("urgent", "boolean")
        conditional = self.question("reason", **self.condition(controller))
        with self.assertRaises(ValidationError) as error:
            validate_questionnaire_response(
                self.questionnaire([controller, conditional]),
                [self.answer(controller, "false"), self.answer(conditional)],
            )
        self.assertEqual(
            error.exception.detail["errors"][0]["type"], "enable_when_failed"
        )

    def test_repeating_groups_and_scalar_values_use_shared_projection(self):
        symptom = self.question("symptom", required=True)
        group = self.question("history", "group", repeats=True, questions=[symptom])
        numbers = self.question("counts", "integer", repeats=True)
        repeated = QuestionnaireSubmitResult.model_validate(
            {
                "question_id": group["id"],
                "sub_results": [
                    [self.answer(symptom, "Headache").model_dump()],
                    [self.answer(symptom, "Fatigue").model_dump()],
                ],
            }
        )
        result = validate_questionnaire_response(
            self.questionnaire([group, numbers]),
            [repeated, self.answer(numbers, values=[{"value": "1"}, {"value": "2"}])],
        )
        self.assertEqual(
            result.cleaned_response,
            {
                "history": [{"symptom": "Headache"}, {"symptom": "Fatigue"}],
                "counts": [1, 2],
            },
        )

    def test_reusing_a_questionnaire_re_evaluates_conditions_for_each_submission(self):
        controller = self.question("urgent", "boolean")
        conditional = self.question(
            "reason", required=True, **self.condition(controller)
        )
        questionnaire = self.questionnaire([controller, conditional])
        validate_questionnaire_response(
            questionnaire, [self.answer(controller, "false")]
        )
        with self.assertRaises(ValidationError):
            validate_questionnaire_response(
                questionnaire, [self.answer(controller, "true")]
            )
        result = validate_questionnaire_response(
            questionnaire, [self.answer(controller, "true"), self.answer(conditional)]
        )
        self.assertEqual(result.cleaned_response, {"urgent": True, "reason": "Answer"})


class QuestionnaireEnginePersistenceTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.code = {
            "system": "http://loinc.org",
            "code": "8310-5",
            "display": "Body temperature",
        }
        self.temperature_id = str(uuid4())
        self.urgent_id = str(uuid4())
        self.questions = [
            {
                "id": self.temperature_id,
                "link_id": "temperature",
                "text": "Temperature",
                "type": "decimal",
                "required": True,
                "code": self.code,
            },
            {
                "id": self.urgent_id,
                "link_id": "urgent",
                "text": "Urgent",
                "type": "boolean",
            },
        ]
        self.encounter_form = baker.make(
            Questionnaire,
            title="Encounter assessment",
            slug="encounter-assessment",
            auth_context="facility",
            facility=self.facility,
            subject_type="encounter",
            status="active",
            questions=deepcopy(self.questions),
        )
        self.facility_form = baker.make(
            Questionnaire,
            title="Facility assessment",
            slug="facility-assessment",
            auth_context="facility",
            facility=self.facility,
            subject_type="facility",
            status="active",
            questions=deepcopy(self.questions),
        )

    def submissions(self, temperature="37.5"):
        submission = QuestionnaireResponseSubmission.model_validate(
            {
                "results": [
                    {
                        "question_id": self.temperature_id,
                        "values": [{"value": temperature}],
                    },
                    {
                        "question_id": self.urgent_id,
                        "values": [{"value": "false"}],
                    },
                ]
            }
        )
        payload = submission.model_dump(mode="json")
        return (
            QuestionnaireSubmitRequest(
                **payload,
                resource_id=self.encounter.external_id,
                encounter=self.encounter.external_id,
                patient=self.patient.external_id,
            ),
            ResourceQuestionnaireSubmitRequest(
                **payload, resource_id=self.facility.external_id
            ),
        )

    def test_existing_handlers_persist_matching_answers_and_observations(self):
        encounter_submission, facility_submission = self.submissions()
        encounter_response = handle_response(
            self.encounter_form, encounter_submission, self.user
        )
        facility_response = handle_resource_response(
            self.facility_form, facility_submission, self.user, self.facility
        )

        encounter_response.refresh_from_db()
        facility_response.refresh_from_db()
        expected = {"temperature": 37.5, "urgent": False}
        self.assertEqual(encounter_response.cleaned_response, expected)
        self.assertEqual(facility_response.cleaned_response, expected)
        self.assertEqual(encounter_response.responses, facility_response.responses)
        self.assertEqual(encounter_response.patient, self.patient)
        self.assertEqual(encounter_response.encounter, self.encounter)
        self.assertEqual(encounter_response.subject_id, self.encounter.external_id)
        self.assertEqual(facility_response.facility, self.facility)
        self.assertEqual(facility_response.subject_id, self.facility.external_id)
        self.assertEqual(QuestionnaireResponse.objects.count(), 1)
        self.assertEqual(FacilityResourceQuestionnaireResponse.objects.count(), 1)

        encounter_observation = Observation.objects.get(
            questionnaire_response=encounter_response
        )
        facility_observation = FacilityResourceObservation.objects.get(
            questionnaire_response=facility_response
        )
        for observation in (encounter_observation, facility_observation):
            with self.subTest(observation=observation):
                self.assertEqual(observation.main_code, self.code)
                self.assertEqual(observation.value_type, "decimal")
                self.assertEqual(observation.value, {"value": "37.5"})
                self.assertEqual(observation.status, "final")
                self.assertEqual(observation.created_by, self.user)
        self.assertEqual(encounter_observation.patient, self.patient)
        self.assertEqual(encounter_observation.encounter, self.encounter)
        self.assertEqual(facility_observation.facility, self.facility)
        self.assertEqual(self.encounter_form.questions, self.questions)
        self.assertEqual(self.facility_form.questions, self.questions)

    def test_existing_handlers_reject_invalid_answers_without_persisting_rows(self):
        encounter_submission, facility_submission = self.submissions("invalid")
        with self.assertRaises(ValidationError):
            handle_response(self.encounter_form, encounter_submission, self.user)
        with self.assertRaises(ValidationError):
            handle_resource_response(
                self.facility_form, facility_submission, self.user, self.facility
            )
        self.assertFalse(QuestionnaireResponse.objects.exists())
        self.assertFalse(FacilityResourceQuestionnaireResponse.objects.exists())
        self.assertFalse(Observation.objects.exists())
        self.assertFalse(FacilityResourceObservation.objects.exists())

    def test_ordinary_actions_exclude_disabled_answers_in_repeating_groups(self):
        controller = {
            "id": str(uuid4()),
            "link_id": "urgent",
            "text": "Urgent",
            "type": "boolean",
        }
        conditional = {
            "id": str(uuid4()),
            "link_id": "count",
            "text": "Count",
            "type": "integer",
            "enable_when": [
                {
                    "question": controller["link_id"],
                    "operator": "equals",
                    "answer": True,
                }
            ],
        }
        group = {
            "id": str(uuid4()),
            "link_id": "history",
            "text": "History",
            "type": "group",
            "repeats": True,
            "questions": [controller, conditional],
        }
        self.encounter_form.questions = [group]
        self.encounter_form.actions = [
            {
                "condition": "'q_count' not in q_history[0] and not q_history[0]['q_urgent']",
                "instructions": [
                    {
                        "slug": "show_message",
                        "context": "self",
                        "params": {"message": "Only validated answers were used"},
                    }
                ],
            }
        ]
        self.encounter_form.save()
        original_questions = deepcopy(self.encounter_form.questions)
        self.client.force_authenticate(user=self.create_super_user())
        url = reverse(
            "questionnaire-submit",
            kwargs={"external_id": self.encounter_form.external_id},
        )

        for disabled_answer in ("99", "invalid"):
            with self.subTest(disabled_answer=disabled_answer):
                response = self.client.post(
                    url,
                    {
                        "resource_id": str(self.encounter.external_id),
                        "patient": str(self.patient.external_id),
                        "encounter": str(self.encounter.external_id),
                        "results": [
                            {
                                "question_id": group["id"],
                                "sub_results": [
                                    [
                                        {
                                            "question_id": controller["id"],
                                            "values": [{"value": "false"}],
                                        },
                                        {
                                            "question_id": conditional["id"],
                                            "values": [{"value": disabled_answer}],
                                        },
                                    ]
                                ],
                            }
                        ],
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(
                    response.data["cleaned_response"],
                    {"history": [{"urgent": False}]},
                )
                self.assertEqual(len(response.data["_actions"]), 1)
                self.assertEqual(
                    response.data["_actions"][0]["results"],
                    {"message": "Only validated answers were used"},
                )
                self.assertEqual(
                    response.data["questionnaire"]["questions"], original_questions
                )
        self.encounter_form.refresh_from_db()
        self.assertEqual(self.encounter_form.questions, original_questions)
