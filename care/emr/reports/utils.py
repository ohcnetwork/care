import logging

from django.utils.timezone import now

from care.emr.models import (
    AllergyIntolerance,
    Condition,
    Encounter,
    FileUpload,
    Observation,
)
from care.emr.models.medication_request import MedicationRequest
from care.facility.models import User

logger = logging.getLogger(__name__)


def handle_condition(options: dict, encounter: Encounter) -> dict:
    """
    Handle the condition data. Supports JSONField (code.display) mapping
    for condition.
    """
    qs = Condition.objects.filter(encounter=encounter)

    for field, values in options.get("filters", {}).items():
        if values:
            qs = qs.filter(**{f"{field}__in": values})

    display_fields = options.get("include", [])
    rows = qs.all()

    table = []

    # Header
    table.append([f.replace("_", " ").title() for f in display_fields])

    for obj in rows:
        row = []
        for field in display_fields:
            match field:
                case "diagnosis" | "symptom":
                    value = obj.code.get("display") if obj.code else "-"
                case "onset":
                    value = obj.onset.get("onset_datetime") if obj.onset else "-"
                case _:
                    value = getattr(obj, field, "-")
            row.append(value if value is not None else "-")
        table.append(row)

    return {"title": options.get("title", "Conditions"), "table": table}


def handle_allergy_intolerance(options: dict, encounter: Encounter) -> dict:
    """
    Handle the allergy intolerance data. Supports JSONField (code.display) mapping
    for allergy intolerance.
    """
    qs = AllergyIntolerance.objects.filter(encounter=encounter)

    for field, values in options.get("filters", {}).items():
        if values:
            qs = qs.filter(**{f"{field}__in": values})

    display_fields = options.get("include", [])
    rows = qs.all()

    table = []

    # Header
    table.append([f.replace("_", " ").title() for f in display_fields])

    for obj in rows:
        row = []
        for field in display_fields:
            match field:
                case "allergen":
                    value = obj.code.get("display") if obj.code else "-"
                case "onset":
                    value = obj.onset.get("onset_datetime") if obj.onset else "-"
                case _:
                    value = getattr(obj, field, "-")
            row.append(value if value is not None else "-")
        table.append(row)

    return {"title": options.get("title", "Allergy Intolerance"), "table": table}


def get_observation_value(observation: Observation) -> str | None:
    if observation.value.get("display", None):
        return observation.value.get("display", None)
    if observation.value.get("unit", None):
        unit: str = observation.value.get("unit", {}).get("display", None)
        value: float | None = observation.value.get("value", None)
        value = int(value) if value and value.is_integer() else value
        return f"{value} {unit}" if unit else value
    return observation.value.get("value", None)


def handle_observation(options: dict, encounter: Encounter) -> dict:
    """
    Handle the observation data. Supports JSONField (main_code.display) mapping
    and formatting for 'value'.
    """
    qs = Observation.objects.filter(encounter=encounter)

    for field, values in options.get("filters", {}).items():
        if values:
            qs = qs.filter(**{f"{field}__in": values})

    display_fields = options.get("include", [])
    rows = qs.all()

    table = []

    # Add header row
    table.append([f.replace("_", " ").title() for f in display_fields])

    for obj in rows:
        row = []
        for field in display_fields:
            match field:
                case "observation":
                    value = obj.main_code.get("display") if obj.main_code else "-"
                case "value":
                    value = get_observation_value(obj)
                case "date":
                    value = obj.effective_datetime or obj.created_date
                case _:
                    value = getattr(obj, field, "-")
            row.append(value if value is not None else "-")
        table.append(row)

    return {"title": options.get("title", "Observations"), "table": table}


def medication_dosage_display(medication: MedicationRequest) -> str:
    try:
        return medication.dosage_instruction[0]["text"]
    except (IndexError, KeyError, TypeError):
        return None


def handle_medication_request(options: dict, encounter: Encounter) -> dict:
    """
    Handle the medication request data. Supports JSONField (code.display) mapping
    for medication request.
    """
    qs = MedicationRequest.objects.filter(encounter=encounter)

    for field, values in options.get("filters", {}).items():
        if values:
            qs = qs.filter(**{f"{field}__in": values})

    display_fields = options.get("include", [])
    rows = qs.all()

    table = []

    # Header
    table.append([f.replace("_", " ").title() for f in display_fields])

    for obj in rows:
        row = []
        for field in display_fields:
            match field:
                case "medication":
                    value = obj.medication.get("display", None)
                case "value":
                    value = medication_dosage_display(obj)
                case "date":
                    value = obj.authored_on or obj.created_date
                case _:
                    value = getattr(obj, field, "-")
            row.append(value if value is not None else "-")
        table.append(row)

    return {"title": options.get("title", "Medication Requests"), "table": table}


def handle_patient_info(options: dict, encounter: Encounter) -> dict:
    """
    Handle the patient info data.
    """
    patient = encounter.patient

    display_fields = options.get("include", [])

    patient_data = {}

    for field in display_fields:
        if field == "date_of_birth":
            if patient.date_of_birth:
                patient_data[field] = patient.date_of_birth
            else:
                patient_data["age"] = patient.get_age()
        if field == "age":
            patient_data[field] = patient.get_age()
        patient_data[field] = getattr(patient, field) or "-"

    return patient_data


def handle_care_team(options: dict, encounter: Encounter) -> dict:
    """
    Format care team into a Typst-compatible table.
    """
    user_roles = {
        member["user_id"]: member["role"]["display"]
        for member in encounter.care_team
        if member.get("user_id") and member.get("role")
    }

    care_team_users = User.objects.filter(id__in=user_roles.keys())

    rows = [
        [user.full_name, user_roles.get(user.id, "Unknown")] for user in care_team_users
    ]

    return {
        "title": options.get("title", "Care Team"),
        "table": [["Name", "Role"], *rows],
    }


def handle_file_display(options: dict, encounter: Encounter) -> dict:
    """
    Handle the file display data.
    """
    qs = FileUpload.objects.filter(
        associating_id=encounter.external_id,
        upload_completed=True,
        is_archived=False,
    )

    display_fields = options.get("include", [])
    rows = qs.all()

    table = []

    # Header
    table.append([f.replace("_", " ").title() for f in display_fields])

    for obj in rows:
        row = []
        for field in display_fields:
            value = getattr(obj, field, "-")
            row.append(value if value is not None else "-")
        table.append(row)

    return {"title": options.get("title", "Files"), "table": table}


def build_discharge_context(encounter: Encounter, config: dict) -> dict:
    """
    Build grouped context from config and encounter.
    Groups:
    - tables → all tabular data
    - patient_info → key-value dict
    - care_team → table
    - files → table
    - discharge_advice → string
    """
    context = {
        "encounter": encounter,
        "patient": encounter.patient,
        "date": now(),
        "tables": [],
        "patient_info": {},
        "care_team": {},
        "files": {},
        "discharge_advice": encounter.discharge_summary_advice or "",
    }

    sections = config.get("sections", {})

    SOURCE_HANDLERS = {  # noqa: N806
        "condition": handle_condition,
        "observation": handle_observation,
        "allergy": handle_allergy_intolerance,
        "medication_request": handle_medication_request,
        "file": handle_file_display,
        "care_team": handle_care_team,
        "patient": handle_patient_info,
        "encounter": lambda *args, **kwargs: {},  # Optional stub
    }

    for section_key, section in sections.items():
        if not isinstance(section, dict) or not section.get("enabled"):
            continue

        source = section.get("source")
        options = section.get("options", {})
        handler = SOURCE_HANDLERS.get(source)

        if not handler:
            # logger.warning(
            #     f"⚠️ No handler for source '{source}' in section '{section_key}'"
            # )
            continue

        try:
            result = handler(options=options, encounter=encounter)
            if not result:
                continue

            title = (
                result.get("title", section_key.replace("_", " ").title())
                if isinstance(result, dict)
                else section_key
            )

            # Group based on section key or source
            if section.get("is_table", False):
                context["tables"].append(
                    {
                        "key": section_key,
                        "source": source,
                        "title": title,
                        "data": result,
                    }
                )
            elif source == "patient":
                context["patient_info"] = result
            elif source == "user":
                context["care_team"] = result
            elif source == "file":
                context["files"] = result
            elif source == "encounter":
                context["discharge_advice"] = result
            else:
                error = f"Unclassified section '{section_key}' - skipping"
                logger.warning(error)

        except Exception as e:
            error = f"Error processing section '{section_key}': {e}"
            logger.exception(error)

    return context
