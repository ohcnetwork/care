"""
FHIR to Questionnaire Handler.

This module provides functionality to convert unsupported FHIR resources
to questionnaire responses, preserving the data in a structured format
where each FHIR data point becomes a separate question.
"""

import json
import logging
import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from care.emr.models import Encounter
from care.emr.models.questionnaire import Questionnaire

User = get_user_model()
logger = logging.getLogger(__name__)


# Slug prefix for auto-generated FHIR questionnaires
FHIR_QUESTIONNAIRE_PREFIX = "fhir-import-"

# FHIR field type mappings to questionnaire question types
FHIR_TYPE_TO_QUESTION_TYPE = {
    "string": "string",
    "code": "string",
    "uri": "url",
    "url": "url",
    "boolean": "boolean",
    "integer": "integer",
    "decimal": "decimal",
    "date": "date",
    "dateTime": "datetime",
    "time": "time",
    "instant": "datetime",
    "positiveInt": "integer",
    "unsignedInt": "integer",
}

# Common FHIR fields and their human-readable labels
FHIR_FIELD_LABELS = {
    "resourceType": "Resource Type",
    "id": "Resource ID",
    "status": "Status",
    "code": "Code",
    "category": "Category",
    "subject": "Subject",
    "patient": "Patient",
    "encounter": "Encounter",
    "performer": "Performer",
    "effectiveDateTime": "Effective Date/Time",
    "effectivePeriod": "Effective Period",
    "issued": "Issued Date",
    "valueString": "Value (String)",
    "valueQuantity": "Value (Quantity)",
    "valueCodeableConcept": "Value (Coded)",
    "valueBoolean": "Value (Boolean)",
    "valueInteger": "Value (Integer)",
    "valueDateTime": "Value (Date/Time)",
    "interpretation": "Interpretation",
    "note": "Notes",
    "bodySite": "Body Site",
    "method": "Method",
    "conclusion": "Conclusion",
    "conclusionCode": "Conclusion Code",
    "result": "Results",
    "component": "Components",
    "identifier": "Identifiers",
    "basedOn": "Based On",
    "partOf": "Part Of",
    "focus": "Focus",
    "context": "Context",
    "reasonCode": "Reason Code",
    "reasonReference": "Reason Reference",
    "relationship": "Relationship",
    "condition": "Conditions",
    "intent": "Intent",
    "priority": "Priority",
    "description": "Description",
    "title": "Title",
    "name": "Name",
    "text": "Text",
}


def _get_question_type_for_value(value: Any) -> str:
    """Determine the appropriate question type based on the value."""
    if value is None:
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "decimal"
    if isinstance(value, (list, dict)):
        return "text"  # Complex types stored as JSON text
    return "string"


def _is_simple_content_array(array: list[dict]) -> tuple[str, list] | None:
    """
    Check if an array contains simple content objects (like FHIR payload with contentString).

    Returns (field_name, values) if all items have a single string field with the same key,
    None otherwise.
    """
    if not array or not all(isinstance(item, dict) for item in array):
        return None

    # Get the keys from the first item
    first_keys = set(array[0].keys())

    # Check if all items have exactly one key and it's a string value
    if len(first_keys) != 1:
        return None

    field_name = list(first_keys)[0]

    # Check all items have the same structure and string values
    values = []
    for item in array:
        if set(item.keys()) != first_keys:
            return None
        val = item.get(field_name)
        if not isinstance(val, (str, int, float, bool)):
            return None
        values.append(val)

    return (field_name, values)


def _flatten_fhir_resource(
    resource: dict[str, Any],
    questions: list[dict],
    responses: list[dict],
    prefix: str = "",
    parent_group_id: str | None = None,
) -> None:
    """
    Recursively flatten a FHIR resource into questions and responses.

    Args:
        resource: The FHIR resource or sub-object
        prefix: The current path prefix (e.g., "code.coding[0]")
        questions: List to append questions to
        responses: List to append responses to
        parent_group_id: ID of the parent group question (for nesting)
    """
    if not isinstance(resource, dict):
        return

    # Fields to skip - these are already part of the metadata or context
    SKIP_FIELDS = {
        "meta", "contained", "extension", "modifierExtension",
        "resourceType", "id",  # Already in metadata
        "patient", "subject", "encounter",  # Already linked via encounter context
    }

    for key, value in resource.items():
        # Skip meta fields and context references
        if key in SKIP_FIELDS:
            continue

        field_path = f"{prefix}.{key}" if prefix else key
        link_id = field_path.replace(".", "_").replace("[", "_").replace("]", "")
        label = FHIR_FIELD_LABELS.get(key, key.replace("_", " ").title())

        if value is None:
            continue

        question_id = str(uuid.uuid4())

        if isinstance(value, dict):
            # Check if it's a simple coding/codeable concept
            if "coding" in value or ("code" in value and "system" in value):
                # Store as structured coding
                question = {
                    "id": question_id,
                    "link_id": link_id,
                    "text": label,
                    "type": "text",
                    "required": False,
                }
                questions.append(question)

                # Format the coding nicely
                if "coding" in value:
                    codings = value.get("coding", [])
                    display_parts = []
                    for coding in codings:
                        display = coding.get("display") or coding.get("code", "")
                        system = coding.get("system", "")
                        code = coding.get("code", "")
                        if display:
                            display_parts.append(f"{display} ({code} - {system})")
                        elif code:
                            display_parts.append(f"{code} ({system})")
                    text_value = value.get("text", "")
                    if text_value and display_parts:
                        formatted = f"{text_value}: {'; '.join(display_parts)}"
                    elif text_value:
                        formatted = text_value
                    else:
                        formatted = "; ".join(display_parts)
                else:
                    # Simple coding
                    display = value.get("display") or value.get("code", "")
                    system = value.get("system", "")
                    code = value.get("code", "")
                    formatted = f"{display} ({code} - {system})" if display else f"{code} ({system})"

                responses.append({
                    "question_id": question_id,
                    "values": [{"value": formatted}],
                    "raw_value": value,
                })

            elif "value" in value and ("unit" in value or "code" in value):
                # Quantity type
                question = {
                    "id": question_id,
                    "link_id": link_id,
                    "text": label,
                    "type": "decimal",
                    "required": False,
                }
                questions.append(question)

                qty_value = value.get("value", "")
                unit = value.get("unit") or value.get("code", "")
                formatted = f"{qty_value} {unit}".strip()

                responses.append({
                    "question_id": question_id,
                    "values": [{
                        "value": str(qty_value) if qty_value is not None else "",
                        "unit": {
                            "code": value.get("code") or value.get("unit"),
                            "display": value.get("unit"),
                            "system": value.get("system"),
                        }
                    }],
                    "raw_value": value,
                })

            elif "start" in value or "end" in value:
                # Period type
                question = {
                    "id": question_id,
                    "link_id": link_id,
                    "text": label,
                    "type": "text",
                    "required": False,
                }
                questions.append(question)

                start = value.get("start", "")
                end = value.get("end", "")
                if start and end:
                    formatted = f"{start} to {end}"
                elif start:
                    formatted = f"From {start}"
                elif end:
                    formatted = f"Until {end}"
                else:
                    formatted = ""

                responses.append({
                    "question_id": question_id,
                    "values": [{"value": formatted}],
                    "raw_value": value,
                })

            elif "reference" in value:
                # Reference type - store the reference string
                question = {
                    "id": question_id,
                    "link_id": link_id,
                    "text": label,
                    "type": "string",
                    "required": False,
                }
                questions.append(question)

                ref = value.get("reference", "")
                display = value.get("display", "")
                formatted = f"{display} ({ref})" if display else ref

                responses.append({
                    "question_id": question_id,
                    "values": [{"value": formatted}],
                    "raw_value": value,
                })

            else:
                # Create a group for nested objects
                group_id = str(uuid.uuid4())
                group_question = {
                    "id": group_id,
                    "link_id": link_id,
                    "text": label,
                    "type": "group",
                    "required": False,
                    "questions": [],
                }

                nested_questions = []
                nested_responses = []
                _flatten_fhir_resource(
                    value, nested_questions, nested_responses, field_path, group_id
                )

                if nested_questions:
                    group_question["questions"] = nested_questions
                    questions.append(group_question)
                    responses.extend(nested_responses)

        elif isinstance(value, list):
            if not value:
                continue

            # Check if it's a list of simple values or complex objects
            first_item = value[0]

            if isinstance(first_item, dict):
                # Check if all items have the same simple structure (like contentString)
                # If so, combine them into a single field
                simple_array = _is_simple_content_array(value)

                if simple_array:
                    # Combine all simple content values into one field
                    field_name, all_values = simple_array
                    combined_label = f"{label} ({field_name})"

                    question = {
                        "id": question_id,
                        "link_id": link_id,
                        "text": combined_label,
                        "type": "text",
                        "required": False,
                    }
                    questions.append(question)

                    # Join all values with newlines
                    combined_value = "\n".join(str(v) for v in all_values if v)
                    responses.append({
                        "question_id": question_id,
                        "values": [{"value": combined_value}],
                        "raw_value": all_values,
                    })
                else:
                    # List of complex objects - create a repeating group
                    group_id = str(uuid.uuid4())
                    group_question = {
                        "id": group_id,
                        "link_id": link_id,
                        "text": label,
                        "type": "group",
                        "required": False,
                        "repeats": True,
                        "questions": [],
                    }

                    # Process all items - collect all values for each field
                    all_nested_questions = []
                    field_values: dict[str, list] = {}  # field_key -> list of (question_id, value)

                    for idx, item in enumerate(value):
                        item_prefix = f"{field_path}[{idx}]"
                        nested_questions = []
                        nested_responses = []
                        _flatten_fhir_resource(
                            item, nested_questions, nested_responses, item_prefix, group_id
                        )

                        if nested_questions and not all_nested_questions:
                            # Use the structure from the first item
                            all_nested_questions = nested_questions

                        # Collect values - map to the corresponding question from first item
                        for i, resp in enumerate(nested_responses):
                            if i < len(all_nested_questions):
                                field_key = all_nested_questions[i].get("link_id", str(i))
                                if field_key not in field_values:
                                    field_values[field_key] = []
                                field_values[field_key].append(resp.get("raw_value"))

                    # Create responses using the question IDs from the first item
                    if all_nested_questions:
                        for q in all_nested_questions:
                            field_key = q.get("link_id")
                            if field_key in field_values:
                                all_vals = field_values[field_key]
                                combined_value = "\n---\n".join(
                                    str(v) for v in all_vals if v is not None
                                )
                                responses.append({
                                    "question_id": q.get("id"),
                                    "values": [{"value": combined_value}],
                                    "raw_value": all_vals,
                                })

                        group_question["questions"] = all_nested_questions
                        questions.append(group_question)

            else:
                # List of simple values
                question = {
                    "id": question_id,
                    "link_id": link_id,
                    "text": label,
                    "type": "text",
                    "required": False,
                    "repeats": True,
                }
                questions.append(question)

                responses.append({
                    "question_id": question_id,
                    "values": [{"value": ", ".join(str(v) for v in value)}],
                    "raw_value": value,
                })

        else:
            # Simple value
            question_type = _get_question_type_for_value(value)
            question = {
                "id": question_id,
                "link_id": link_id,
                "text": label,
                "type": question_type,
                "required": False,
            }
            questions.append(question)

            responses.append({
                "question_id": question_id,
                "values": [{"value": str(value)}],
                "raw_value": value,
            })


def get_or_create_fhir_questionnaire(
    resource_type: str,
    fhir_resource: dict[str, Any],
) -> tuple[Questionnaire, list[dict]]:
    """
    Get or create a questionnaire for storing FHIR resources of a given type.

    Creates a structured questionnaire where each FHIR field becomes a question.

    Args:
        resource_type: The FHIR resource type (e.g., "DiagnosticReport")
        fhir_resource: The FHIR resource to base the structure on

    Returns:
        Tuple of (Questionnaire object, responses list)
    """
    slug = f"{FHIR_QUESTIONNAIRE_PREFIX}{resource_type.lower()}"

    # Generate questions and responses from the FHIR resource
    questions = []
    responses = []
    _flatten_fhir_resource(fhir_resource, questions, responses)

    # Try to get existing questionnaire
    questionnaire = Questionnaire.objects.filter(slug=slug).first()

    if questionnaire:
        # Update questions if the new resource has more fields
        existing_link_ids = {q.get("link_id") for q in questionnaire.questions}
        new_questions = [q for q in questions if q.get("link_id") not in existing_link_ids]

        if new_questions:
            # Merge new questions into existing questionnaire
            updated_questions = questionnaire.questions + new_questions
            questionnaire.questions = updated_questions
            questionnaire.save(update_fields=["questions"])
            logger.info(f"Updated FHIR import questionnaire with {len(new_questions)} new questions: {slug}")

        # Map responses to existing question IDs
        questions_by_link_id = {q.get("link_id"): q for q in questionnaire.questions}
        mapped_responses = []
        for resp in responses:
            # Find the corresponding question by link_id
            for q in questions:
                if q.get("id") == resp.get("question_id"):
                    link_id = q.get("link_id")
                    if link_id in questions_by_link_id:
                        mapped_responses.append({
                            "question_id": questions_by_link_id[link_id]["id"],
                            "values": resp.get("values", []),
                            "raw_value": resp.get("raw_value"),
                        })
                    break

        return questionnaire, mapped_responses

    # Create a new questionnaire for this FHIR resource type
    with transaction.atomic():
        # Double-check to avoid race conditions
        questionnaire = Questionnaire.objects.filter(slug=slug).first()
        if questionnaire:
            return get_or_create_fhir_questionnaire(resource_type, fhir_resource)

        questionnaire = Questionnaire.objects.create(
            slug=slug,
            title=f"FHIR {resource_type}",
            description=(
                f"Auto-generated structured questionnaire for storing imported FHIR "
                f"{resource_type} resources. Each field in the FHIR resource is "
                f"mapped to a question for structured data capture."
            ),
            version="1.0",
            status="active",
            subject_type="encounter",
            questions=questions,
            styling_metadata={
                "is_fhir_import": True,
                "fhir_resource_type": resource_type,
            },
        )

        logger.info(f"Created FHIR import questionnaire with {len(questions)} questions: {slug}")

    return questionnaire, responses


def create_questionnaire_response_for_fhir(
    questionnaire: Questionnaire,
    responses: list[dict],
    fhir_resource: dict[str, Any],
    encounter: Encounter,
    user: User,
) -> dict[str, Any]:
    """
    Create a questionnaire response from a FHIR resource.

    Args:
        questionnaire: The questionnaire to submit the response to
        responses: The pre-generated responses list
        fhir_resource: The original FHIR resource data
        encounter: The encounter context
        user: The user creating the response

    Returns:
        Dictionary with the created response details
    """
    from care.emr.models import QuestionnaireResponse

    resource_type = fhir_resource.get("resourceType", "Unknown")
    resource_id = fhir_resource.get("id")

    # Clean responses for storage (remove raw_value, keep only question_id and values)
    clean_responses = [
        {"question_id": r["question_id"], "values": r["values"]}
        for r in responses
    ]

    # Create structured responses with all field values for easy querying
    structured_responses = {
        "_fhir_resource_type": resource_type,
        "_fhir_resource_id": resource_id,
        "_fhir_resource": fhir_resource,
    }

    # Add individual field values to structured responses
    for resp in responses:
        if resp.get("raw_value") is not None:
            # Find the link_id for this question
            for q in questionnaire.questions:
                if q.get("id") == resp.get("question_id"):
                    structured_responses[q.get("link_id")] = resp.get("raw_value")
                    break

    # Create the questionnaire response
    questionnaire_response = QuestionnaireResponse.objects.create(
        questionnaire=questionnaire,
        subject_id=encounter.external_id,
        patient=encounter.patient,
        encounter=encounter,
        responses=clean_responses,
        structured_responses=structured_responses,
        structured_response_type=f"fhir_{resource_type.lower()}",
        status="completed",
        created_by=user,
        updated_by=user,
    )

    return {
        "questionnaire_response_id": str(questionnaire_response.external_id),
        "questionnaire_slug": questionnaire.slug,
        "fields_captured": len(clean_responses),
    }


class FHIRQuestionnaireProcessor:
    """
    Processor for converting unsupported FHIR resources to questionnaire responses.

    This processor serves as a fallback for FHIR resource types that don't have
    a direct mapping in the care system. It creates a structured questionnaire
    where each FHIR field becomes a separate question, preserving all data points.

    Usage:
        processor = FHIRQuestionnaireProcessor(encounter, user)
        result = processor.process(fhir_resource)
    """

    def __init__(self, encounter: Encounter, user: User):
        """
        Initialize the processor.

        Args:
            encounter: The encounter context
            user: The user creating the resources
        """
        self.encounter = encounter
        self.user = user

    def process(self, fhir_resource: dict[str, Any]) -> dict[str, Any]:
        """
        Process a FHIR resource and create a questionnaire response.

        Args:
            fhir_resource: The FHIR resource data

        Returns:
            Processing result dictionary
        """
        resource_type = fhir_resource.get("resourceType", "Unknown")

        result = {
            "success": False,
            "resource_type": resource_type,
            "fhir_id": fhir_resource.get("id"),
            "stored_as": "questionnaire_response",
        }

        try:
            # Get or create the questionnaire and generate responses
            questionnaire, responses = get_or_create_fhir_questionnaire(
                resource_type, fhir_resource
            )

            # Create the questionnaire response
            response_result = create_questionnaire_response_for_fhir(
                questionnaire=questionnaire,
                responses=responses,
                fhir_resource=fhir_resource,
                encounter=self.encounter,
                user=self.user,
            )

            result["success"] = True
            result["care_id"] = response_result["questionnaire_response_id"]
            result["questionnaire_slug"] = response_result["questionnaire_slug"]
            result["fields_captured"] = response_result["fields_captured"]

        except Exception as e:
            logger.exception(f"Error processing FHIR {resource_type} as questionnaire: {e}")
            result["errors"] = [str(e)]

        return result
