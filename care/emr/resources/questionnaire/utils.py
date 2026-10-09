import uuid
from datetime import datetime
from decimal import InvalidOperation
from urllib.parse import urlparse

from dateutil.parser import isoparse
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from care.emr.models.encounter import Encounter
from care.emr.models.facility_resource import (
    FacilityResourceObservation,
    FacilityResourceQuestionnaireResponse,
)
from care.emr.models.observation import Observation
from care.emr.models.patient import Patient
from care.emr.models.questionnaire import Questionnaire, QuestionnaireResponse
from care.emr.models.valueset import ValueSet
from care.emr.resources.observation.resource_spec import ResourceObservationSpec
from care.emr.resources.observation.spec import ObservationSpec, ObservationStatus
from care.emr.resources.questionnaire.spec import QuestionnaireAuthContext, QuestionType
from care.emr.resources.valueset.spec import ValueSetAuthContext
from care.utils.rounding.covert_type import convert_to_decimal

BOOLEAN_TRUE_STRINGS = ("true", "on", "ok", "y", "yes", "1")
BOOLEAN_FALSE_STRINGS = ("false", "off", "no", "n", "0")


def validate_questionnaire_valueset(valueset_config, code):
    if isinstance(valueset_config, str):
        valueset = ValueSet.objects.filter(
            slug=valueset_config, auth_context=ValueSetAuthContext.instance
        ).first()
    elif valueset_config.get("external_id"):
        valueset = ValueSet.objects.filter(
            external_id=valueset_config["external_id"]
        ).first()
    else:
        valueset = ValueSet.objects.filter(
            slug=valueset_config.get("slug"),
            auth_context="instance",
        ).first()
    if code is None:
        raise ValueError("Code is required")
    if not valueset or not valueset.lookup(code):
        raise ValueError("Code does not exist in the value set")
    return code


def create_responses_mapping(results_list):
    """
    Creates a mapping of question IDs to their responses.

    Args:
        results_list: List of question results
    Returns:
        dict: Mapping of question IDs to their responses
    """
    responses = {}
    for result in results_list:
        responses[str(result.question_id)] = result
    return responses


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
                convert_to_decimal(value.value)
            elif value_type == QuestionType.boolean.value:
                if value.value.lower() not in ["true", "false", "1", "0"]:
                    errors.append(f"Invalid boolean value: {value.value}")
            elif value_type == QuestionType.date.value:
                isoparse(value.value).date()
            elif value_type == QuestionType.datetime.value:
                parsed_dt = isoparse(value.value)
                if timezone.is_naive(parsed_dt):
                    errors.append("DateTime must include timezone information")
            elif value_type == QuestionType.time.value:
                datetime.strptime(value.value, "%H:%M:%S")  # noqa DTZ007
            elif value_type == QuestionType.choice.value:
                if value.value not in get_valid_choices(questionnaire_ref):
                    errors.append(f"Invalid {value_type}")
            elif value_type == QuestionType.url.value:
                parsed = urlparse(value.value)
                if not all([parsed.scheme, parsed.netloc]):
                    errors.append(f"Invalid {value_type}")
            elif (
                value_type == QuestionType.text.value
                and len(value.value) > settings.MAX_QUESTIONNAIRE_TEXT_RESPONSE_SIZE
            ):
                error = f"Text too long. Max allowed size is {settings.MAX_QUESTIONNAIRE_TEXT_RESPONSE_SIZE}"
                errors.append(error)
        except (ValueError, InvalidOperation):
            errors.append(f"Invalid {value_type}")
        except Exception:
            errors.append(f"Error validating {value_type}")

    return errors


def normalize_boolean_value(value):
    """
    Convert BOOLEAN_TRUE_STRING and BOOLEAN_FALSE_STRING to proper boolean values.

    This helps when comparing condition values in `enable_when`, where
    answers may come as strings but actually mean True or False.

    If the value doesn't look like a boolean, return it as-is.
    """
    if isinstance(value, str):
        val = value.strip().lower()
        if val in BOOLEAN_TRUE_STRINGS:
            return True
        if val in BOOLEAN_FALSE_STRINGS:
            return False
    return value


def is_question_enabled(question, responses, questionnaire_obj):  # noqa PLR0912
    """
    Check if a question should be enabled based on its enable_when conditions.
    Returns True if the question is enabled, False otherwise.
    """
    question_link_id_to_id = get_link_id_map(questionnaire_obj.questions)

    if not question.get("enable_when"):
        return True

    conditions = question["enable_when"]
    behavior = question.get("enable_behavior", "all")
    results = []

    for condition in conditions:
        link_id = condition["question"]
        if link_id not in question_link_id_to_id:
            results.append(False)
            continue

        condition_question_id = question_link_id_to_id[link_id]

        if (
            condition_question_id not in responses
            or not responses[condition_question_id].values
        ):
            all_values = []
        else:
            all_values = [
                normalize_boolean_value(v.value)
                for v in responses[condition_question_id].values
            ]

        operator = condition["operator"]
        expected_answer = normalize_boolean_value(condition["answer"])

        # Evaluate the condition across all values
        if operator == "exists":
            result = bool(all_values) if expected_answer else not bool(all_values)
        elif operator == "equals":
            result = expected_answer in all_values
        elif operator == "not_equals":
            result = bool(all_values) and all(v != expected_answer for v in all_values)
        elif operator == "greater":
            try:
                result = any(
                    convert_to_decimal(v) > convert_to_decimal(expected_answer)
                    for v in all_values
                )
            except (TypeError, ValueError):
                result = False
        elif operator == "less":
            try:
                result = any(
                    convert_to_decimal(v) < convert_to_decimal(expected_answer)
                    for v in all_values
                )
            except (TypeError, ValueError):
                result = False
        elif operator == "greater_or_equals":
            try:
                result = any(
                    convert_to_decimal(v) >= convert_to_decimal(expected_answer)
                    for v in all_values
                )
            except (TypeError, ValueError):
                result = False
        elif operator == "less_or_equals":
            try:
                result = any(
                    convert_to_decimal(v) <= convert_to_decimal(expected_answer)
                    for v in all_values
                )
            except (TypeError, ValueError):
                result = False
        else:
            result = False

        results.append(result)

    # Combine condition results using the enable_behavior.
    return all(results) if behavior == "all" else any(results)


def validate_question_result(  # noqa: PLR0911, PLR0912
    questionnaire, responses, errors, parent, questionnaire_mapping
):
    questionnaire["parent"] = parent
    # Validate question responses
    if questionnaire["type"] == QuestionType.structured.value:
        return
    if questionnaire["type"] == QuestionType.group.value:
        # Iterate and call all child questions
        questionnaire_mapping[questionnaire["id"]] = questionnaire
        if questionnaire.get("questions"):
            if questionnaire.get("repeats", False):
                # Handle repeating groups
                response = responses.get(questionnaire["id"])
                if not response or not response.sub_results:
                    return
                for sub_responses in response.sub_results:
                    question = questionnaire.copy()
                    question["repeats"] = False  # Set to false to avoid infinite loop
                    validate_question_result(
                        question,
                        create_responses_mapping(sub_responses),
                        errors,
                        questionnaire["id"],
                        questionnaire_mapping,
                    )
            else:
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
                if not value.coding:
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
                        validate_questionnaire_valueset(
                            questionnaire["answer_value_set"],
                            value.coding,
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
                if not value.unit:
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
                        validate_questionnaire_valueset(
                            questionnaire["answer_value_set"],
                            value.coding,
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


def create_observation_spec(questionnaire, response, parent_id=None):
    spec = {
        "status": ObservationStatus.final.value,
        "value_type": questionnaire["type"],
    }
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
    if getattr(response, "values", []):
        observation = {}
        for value in response.values:
            observation = spec.copy()
            observation["id"] = str(uuid.uuid4())
            if questionnaire["type"] == QuestionType.choice.value and value.coding:
                observation["value"] = {
                    "coding": value.coding.model_dump(exclude_defaults=True),
                }

            elif questionnaire["type"] == QuestionType.quantity.value and value.coding:
                observation["value"] = {
                    "unit": questionnaire.get("unit"),
                    "value": value.value,
                    "coding": value.coding.model_dump(exclude_defaults=True),
                }
            elif value:
                observation["value"] = {"value": value.value}
                if "unit" in questionnaire:
                    observation["value"]["unit"] = questionnaire["unit"]
            if response.note:
                observation["note"] = response.note
        if parent_id:
            observation["parent"] = parent_id
        observation["effective_datetime"] = timezone.now()
        observations.append(observation)
    return observations


def create_components(questionnaire, responses):
    components = []
    observations = convert_to_observation_spec(
        questionnaire, responses, is_component=True
    )
    # Convert from observation spec into component spec
    # Need to handle how body site and method works in these cases
    # These values need to be ignored when is_component is selected in the FE and in the validations
    for observation in observations:
        if "main_code" not in observation or "value" not in observation:
            continue
        component = {"value": observation["value"], "code": observation["main_code"]}
        if "note" in observation:
            component["note"] = observation["note"]
        components.append(component)
    return components


def convert_to_observation_spec(
    questionnaire, responses, parent_id=None, is_component=False
):
    constructed_observation_mapping = []
    for question in questionnaire.get("questions", []):
        response = responses.get(question["id"])
        if question["type"] == QuestionType.group.value:
            if not is_component and question.get("is_component", False):
                if question.get("repeats", False) and getattr(
                    response, "sub_results", None
                ):
                    # create components for repeating groups
                    for sub_responses in response.sub_results:
                        observation = create_observation_spec(question, None, parent_id)
                        observation[0]["component"] = create_components(
                            question, create_responses_mapping(sub_responses)
                        )
                        constructed_observation_mapping.extend(observation)
                else:
                    # create components for non-repeating groups
                    observation = create_observation_spec(question, None, parent_id)
                    observation[0]["component"] = create_components(question, responses)
                    constructed_observation_mapping.extend(observation)
            else:
                observation = create_observation_spec(question, None, parent_id)
                sub_mapping = convert_to_observation_spec(
                    question, responses, observation[0]["id"]
                )
                if sub_mapping:
                    constructed_observation_mapping.extend(observation)
                    constructed_observation_mapping.extend(sub_mapping)
        elif question.get("code"):
            constructed_observation_mapping.extend(
                create_observation_spec(question, response, parent_id)
            )

    return constructed_observation_mapping


def _dump_coding(coding):
    if not coding:
        return None
    return coding.model_dump(exclude_defaults=True, exclude_none=True)


def _coerce_cleaned_value(raw_value, question_type):
    if raw_value is None:
        return None
    if question_type == QuestionType.boolean.value:
        return normalize_boolean_value(raw_value)
    if question_type == QuestionType.integer.value:
        return int(raw_value)
    if question_type in [QuestionType.decimal.value, QuestionType.quantity.value]:
        return float(convert_to_decimal(raw_value))
    return raw_value


def _clean_result_value(question, value):
    question_type = question["type"]
    coding = _dump_coding(value.coding)
    unit = _dump_coding(value.unit)
    cleaned_value = _coerce_cleaned_value(value.value, question_type)

    if coding or unit:
        cleaned = {}
        if cleaned_value is not None:
            cleaned["value"] = cleaned_value
        if coding:
            cleaned["coding"] = coding
        if unit:
            cleaned["unit"] = unit
        return cleaned

    return cleaned_value


def _clean_question_response(question, response):
    values = getattr(response, "values", None) or []
    cleaned_values = [
        _clean_result_value(question, value)
        for value in values
        if value.value is not None or value.coding or value.unit
    ]
    if not cleaned_values:
        return None
    if question.get("repeats", False) or len(cleaned_values) > 1:
        return cleaned_values
    return cleaned_values[0]


def build_cleaned_response(questions, responses, prefix=""):
    """
    Build a query-friendly response projection keyed by questionnaire link_id.
    """
    cleaned_response = {}
    for question in questions:
        link_id = question["link_id"]
        response = responses.get(question["id"])

        if question["type"] == QuestionType.group.value:
            if question.get("repeats", False):
                if not response or not getattr(response, "sub_results", None):
                    continue
                group_values = []
                for sub_results in response.sub_results:
                    group_value = build_cleaned_response(
                        question.get("questions", []),
                        create_responses_mapping(sub_results),
                        prefix,
                    )
                    if group_value:
                        group_values.append(group_value)
                if group_values:
                    cleaned_response[prefix + link_id] = group_values
            else:
                cleaned_response.update(
                    build_cleaned_response(
                        question.get("questions", []), responses, prefix
                    )
                )
            continue

        if not response:
            continue

        cleaned_value = _clean_question_response(question, response)
        if cleaned_value is not None:
            cleaned_response[prefix + link_id] = cleaned_value

    return cleaned_response


def collect_and_validate_enable_when_questions(
    questions, responses, questionnaire_obj, errors, parent=None
):
    """Filter questions by ``enable_when`` rules and record related errors.

    Algorithm:

    - If a question's ``enable_when`` evaluates to False and the question (or any
      of its descendant questions) has answers, an ``enable_when_failed`` error
      is appended to ``errors``.
    - Enabled groups are traversed recursively and pruned so that only their
      enabled descendants remain.

    Returns:
        list: The filtered list of enabled questions (with nested structure
        preserved for groups that remain enabled).
    """

    def any_answered(q, resp_map):
        resp = resp_map.get(q["id"])

        # Direct answer for simple question
        if resp and getattr(resp, "values", None):
            return True

        # Repeating group: inspect sub_results
        if resp and getattr(resp, "sub_results", None):
            for sub in resp.sub_results:
                sub_resp_map = create_responses_mapping(sub)
                if any_answered(q, sub_resp_map):
                    return True

        # Recursively check child questions if present (for nested groups)
        if q.get("questions"):
            return any(any_answered(child, resp_map) for child in q["questions"])

        return False

    valid = []
    for q in questions:
        is_enabled = is_question_enabled(q, responses, questionnaire_obj)

        if not is_enabled:
            if any_answered(q, responses):
                errors.append(
                    {
                        "question_id": q["id"],
                        "type": "enable_when_failed",
                        "msg": (
                            f"Question or group '{q.get('link_id', q['id'])}' "
                            "is not permitted by its enable_when conditions"
                        ),
                    }
                )
            continue  # skip this question/group

        # Recurse into groups
        if q["type"] == QuestionType.group.value and q.get(
            "questions"
        ):  # this ignores the case where a group has no questions
            grp = q.copy()
            grp["questions"] = collect_and_validate_enable_when_questions(
                q["questions"], responses, questionnaire_obj, errors, parent=q["id"]
            )
            valid.append(grp)
        else:
            valid.append(q)

    return valid


def get_link_id_map(questions):
    """
    Recursively extract a map of link_id to question_id from all questions, including nested ones.
    """
    mapping = {}
    for q in questions:
        mapping[q["link_id"]] = q["id"]
        if q.get("questions"):
            mapping.update(get_link_id_map(q["questions"]))
    return mapping


def handle_response(questionnaire_obj: Questionnaire, results, user):
    """
    Generate observations and questionnaire responses after validation
    """
    if questionnaire_obj.status != "active":
        raise ValidationError(
            {"type": "questionnaire_inactive", "msg": "Questionnaire is inactive"}
        )

    # Construct questionnaire response

    if questionnaire_obj.subject_type == "patient":
        if questionnaire_obj.auth_context != QuestionnaireAuthContext.instance:
            raise ValidationError(
                "Patient questionnaires are only supported at the instance level"
            )
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
    errors = []

    responses = create_responses_mapping(results.results)
    if not responses:
        raise ValidationError(
            {
                "type": "questionnaire_empty",
                "msg": "Empty Questionnaire cannot be submitted",
            }
        )

    questionnaire_obj.questions = collect_and_validate_enable_when_questions(
        questionnaire_obj.questions, responses, questionnaire_obj, errors
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
        cleaned_response=build_cleaned_response(questionnaire_obj.questions, responses),
        created_by=user,
        updated_by=user,
    )
    questionnaire_response._responses = responses  # noqa SLF001
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


def handle_resource_response(questionnaire_obj: Questionnaire, results, user, facility):
    """
    Generate observations and questionnaire responses after validation for resource questionnaires
    """
    if questionnaire_obj.status != "active":
        raise ValidationError(
            {"type": "questionnaire_inactive", "msg": "Questionnaire is inactive"}
        )

    # Construct questionnaire response

    questionnaire_mapping = {}
    errors = []

    responses = create_responses_mapping(results.results)
    if not responses:
        raise ValidationError(
            {
                "type": "questionnaire_empty",
                "msg": "Empty Questionnaire cannot be submitted",
            }
        )

    questionnaire_obj.questions = collect_and_validate_enable_when_questions(
        questionnaire_obj.questions, responses, questionnaire_obj, errors
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

    # Create questionnaire response
    json_results = results.model_dump(mode="json", exclude_defaults=True)
    questionnaire_response = FacilityResourceQuestionnaireResponse.objects.create(
        facility=facility,
        questionnaire=questionnaire_obj,
        subject_type=questionnaire_obj.subject_type,
        subject_id=results.resource_id,
        responses=json_results["results"],
        cleaned_response=build_cleaned_response(questionnaire_obj.questions, responses),
        created_by=user,
        updated_by=user,
    )

    # Bulk create observations
    observations_objects = [
        ResourceObservationSpec(
            **observation,
            subject_type=questionnaire_obj.subject_type,
            subject_id=results.resource_id,
            data_entered_by_id=user.id,
            created_by_id=user.id,
            updated_by_id=user.id,
            facility_id=facility.id,
            questionnaire_response_id=questionnaire_response.id,
        )
        for observation in observations
    ]
    # Serialize and return questionnaire response
    bulk = []
    for observation in observations_objects:
        temp = observation.de_serialize()
        bulk.append(temp)

    FacilityResourceObservation.objects.bulk_create(bulk)

    return questionnaire_response
