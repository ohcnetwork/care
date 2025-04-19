from care.emr.models import AllergyIntolerance, Condition, Encounter, Observation
from care.emr.models.medication_request import MedicationRequest


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

    table = list

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

    table = list

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

    table = list

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

    table = list

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
