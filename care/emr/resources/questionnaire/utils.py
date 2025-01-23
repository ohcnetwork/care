import uuid
from datetime import datetime
from urllib.parse import urlparse

from dateutil.parser import isoparse
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from care.emr.models.encounter import Encounter
from care.emr.models.observation import Observation
from care.emr.models.patient import Patient
from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.observation.spec import ObservationSpec, ObservationStatus
from care.emr.resources.questionnaire.spec import QuestionType


def check_required(questionnaire, questionnaire_ref):
    """
    Recursively check if the question is marked as required anywhere in its parents
    """
    if questionnaire.get("required", False):
        return True
    if questionnaire.get("parent"):
        return check_required(
            questionnaire_ref[questionnaire.get("parent")], questionnaire_ref
        )
    return False


def get_valid_choices(question):
    """
    Extracts valid choices from a choice question dictionary.
    """
    answer_options = question.get("answer_option", [])
    if not answer_options:
        error = f"No 'answer_option' found in question with id {question.get('id')}."
        raise ValueError(error)

    return [option["value"] for option in answer_options if "value" in option]


def validate_data(values, value_type, questionnaire_ref):  # noqa PLR0912
    """
    Validate the type of the value based on the question type.
    Args:
        values: List of values to validate
        value_type: Type of the question (from QuestionType enum)
    Returns:
        list: List of validation errors, empty if validation succeeds
    """
    errors = []
    if not values:
        return errors
    for value in values:
        if value.value is None:
            continue
        try:
            if value_type == QuestionType.integer.value:
                int(value.value)
            elif value_type == QuestionType.decimal.value:
                float(value.value)
            elif value_type == QuestionType.boolean.value:
                if value.value.lower() not in ["true", "false", "1", "0"]:
                    errors.append(f"Invalid boolean value: {value.value}")
            elif value_type == QuestionType.date.value:
                isoparse(value.value).date()
            elif value_type == QuestionType.datetime.value:
                isoparse(value.value)
            elif value_type == QuestionType.time.value:
                datetime.strptime(value.value, "%H:%M:%S")  # noqa DTZ007
            elif value_type == QuestionType.choice.value:
                if value.value not in get_valid_choices(questionnaire_ref):
                    errors.append(f"Invalid {value_type}")
            elif value_type == QuestionType.url.value:
                parsed = urlparse(value.value)
                if not all([parsed.scheme, parsed.netloc]):
                    errors.append(f"Invalid {value_type}")
        except ValueError:
            errors.append(f"Invalid {value_type}")
        except Exception:
            errors.append(f"Error validating {value_type}")

    return errors


def validate_question_result(  # noqa : PLR0912
    questionnaire, responses, errors, parent, questionnaire_mapping
):
    questionnaire["parent"] = parent
    # Validate question responses
    if questionnaire["type"] == QuestionType.structured.value:
        return
    if questionnaire["type"] == QuestionType.group.value:
        # Iterate and call all child questions
        questionnaire_mapping[questionnaire["id"]] = questionnaire
        if questionnaire["questions"]:
            for question in questionnaire["questions"]:
                validate_question_result(
                    question,
                    responses,
                    errors,
                    questionnaire["id"],
                    questionnaire_mapping,
                )
    else:
        # Case when question is not answered ( Not in response )
        if questionnaire["id"] not in responses and questionnaire.get(
            "required", False
        ):
            errors.append(
                {"question_id": questionnaire["id"], "error": "Question not answered"}
            )
            return
        if questionnaire["id"] not in responses:
            return
        values = responses[questionnaire["id"]].values
        # Case when the question is answered but is empty
        if not values and check_required(questionnaire, questionnaire_mapping):
            err = "No value provided for question"
            errors.append(
                {
                    "question_id": questionnaire["id"],
                    "type": "values_missing",
                    "msg": err,
                }
            )
            return
        # Check for type errors
        value_type = questionnaire["type"]
        if questionnaire.get("repeats", False):
            values = responses[questionnaire["id"]].values[0:1]
        type_errors = validate_data(values, value_type, questionnaire)
        if type_errors:
            errors.extend(
                [
                    {
                        "type": "type_error",
                        "question_id": questionnaire["id"],
                        "msg": error,
                    }
                    for error in type_errors
                ]
            )
        # Validate for code and quantity
        if questionnaire["type"] == QuestionType.choice.value and questionnaire.get(
            "answer_value_set"
        ):
            for value in values:
                if not value.value_code:
                    errors.append(
                        {
                            "type": "type_error",
                            "question_id": questionnaire["id"],
                            "msg": "Coding is required",
                        }
                    )
                    return
                # Validate code
                if "answer_value_set" in questionnaire:
                    try:
                        validate_valueset(
                            "unit", questionnaire["answer_value_set"], value.value_code
                        )
                    except ValueError:
                        errors.append(
                            {
                                "type": "valueset_error",
                                "question_id": questionnaire["id"],
                                "msg": "Coding does not belong to the valueset",
                            }
                        )
        # TODO : Validate for options created by user as well
        if questionnaire["type"] == QuestionType.quantity.value:
            for value in values:
                if not value.value_quantity:
                    errors.append(
                        {
                            "type": "type_error",
                            "question_id": questionnaire["id"],
                            "msg": "Quantity is required",
                        }
                    )
                    return
                # Validate code
                # TODO : Validate for options created by user as well
                if "answer_value_set" in questionnaire:
                    try:
                        validate_valueset(
                            "unit",
                            questionnaire["answer_value_set"],
                            value.value_quantity.code,
                        )
                    except ValueError:
                        errors.append(
                            {
                                "type": "valueset_error",
                                "question_id": questionnaire["id"],
                                "msg": "Coding does not belong to the valueset",
                            }
                        )
        # ( check if the code belongs to the valueset or options list)


def create_observation_spec(questionnaire, responses, parent_id=None):
    spec = {}
    spec["status"] = ObservationStatus.final.value
    spec["value_type"] = questionnaire["type"]
    if "category" in questionnaire:
        spec["category"] = questionnaire["category"]
    if "code" in questionnaire:
        spec["main_code"] = questionnaire["code"]
    if questionnaire["type"] == QuestionType.group.value:
        spec["id"] = str(uuid.uuid4())
        spec["effective_datetime"] = timezone.now()
        spec["value"] = {}
        return [spec]
    observations = []
    if (
        responses
        and questionnaire["id"] in responses
        and responses[questionnaire["id"]].values
        and responses[questionnaire["id"]].values[0]
    ):
        for value in responses[questionnaire["id"]].values:
            observation = spec.copy()
            observation["id"] = str(uuid.uuid4())
            if questionnaire["type"] == QuestionType.choice.value and value.value_code:
                observation["value"] = {
                    "value_code": (value.value_code.model_dump(exclude_defaults=True))
                }
            elif (
                questionnaire["type"] == QuestionType.quantity.value
                and value.value_quantity
            ):
                observation["value"] = {
                    "value_quantity": (
                        value.value_quantity.model_dump(exclude_defaults=True)
                    )
                }
            elif value:
                observation["value"] = {"value": value.value}
            if responses[questionnaire["id"]].note:
                observation["note"] = responses[questionnaire["id"]].note
        if parent_id:
            observation["parent"] = parent_id
        observation["effective_datetime"] = timezone.now()
        observations.append(observation)
    return observations


def convert_to_observation_spec(
    questionnaire_obj: Questionnaire, responses, parent_id=None
):
    constructed_observation_mapping = []
    for question in questionnaire_obj.get("questions", []):
        if question["type"] == QuestionType.group.value:
            observation = create_observation_spec(question, responses, parent_id)
            sub_mapping = convert_to_observation_spec(
                question, responses, observation[0]["id"]
            )
            if sub_mapping:
                constructed_observation_mapping.extend(observation)
                constructed_observation_mapping.extend(sub_mapping)
        elif question.get("code"):
            constructed_observation_mapping.extend(
                create_observation_spec(question, responses, parent_id)
            )

    return constructed_observation_mapping


def handle_response(questionnaire_obj: Questionnaire, results, user):
    """
    Generate observations and questionnaire responses after validation
    """
    # Construct questionnaire response

    if questionnaire_obj.subject_type == "patient":
        encounter = None
    else:
        encounter = Encounter.objects.filter(external_id=results.encounter).first()
        if not encounter:
            raise ValidationError(
                {"type": "object_not_found", "msg": "Encounter not found"}
            )

    patient = Patient.objects.filter(external_id=results.patient).first()
    if not patient:
        raise ValidationError({"type": "object_not_found", "msg": "Patient not found"})

    questionnaire_mapping = {}
    responses = {}
    errors = []
    for result in results.results:
        responses[str(result.question_id)] = result
    if not responses:
        raise ValidationError(
            {
                "type": "questionnaire_empty",
                "msg": "Empty Questionnaire cannot be submitted",
            }
        )
    for question in questionnaire_obj.questions:
        validate_question_result(
            question,
            responses,
            errors,
            parent=None,
            questionnaire_mapping=questionnaire_mapping,
        )
    if errors:
        raise ValidationError({"errors": errors})
    # Validate and create observation objects
    observations = convert_to_observation_spec(
        {"questions": questionnaire_obj.questions}, responses
    )
    # Bulk create observations
    observations_objects = [
        ObservationSpec(
            **observation,
            subject_type=questionnaire_obj.subject_type,
            data_entered_by_id=user.id,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        for observation in observations
    ]

    # Create questionnaire response
    json_results = results.model_dump(mode="json", exclude_defaults=True)
    questionnaire_response = QuestionnaireResponse.objects.create(
        questionnaire=questionnaire_obj,
        subject_id=results.resource_id,
        encounter=encounter,
        patient=patient,
        responses=json_results["results"],
        created_by=user,
        updated_by=user,
    )
    # Serialize and return questionnaire response
    if encounter:
        bulk = []
        for observation in observations_objects:
            temp = observation.de_serialize()
            temp.questionnaire_response = questionnaire_response
            temp.subject_id = results.resource_id
            temp.patient = patient
            temp.encounter = encounter
            bulk.append(temp)

        Observation.objects.bulk_create(bulk)

    return questionnaire_response
