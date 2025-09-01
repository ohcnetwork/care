from django import template

from care.emr.models.medication_request import MedicationRequest
from care.emr.models.observation import Observation
from care.emr.resources.encounter.constants import (
    ClassChoices,
)
from care.emr.resources.encounter.enum_display_names import (
    get_admit_source_display,
    get_discharge_disposition_display,
)

register = template.Library()


@register.filter
def admit_source_display(value: str) -> str:
    return get_admit_source_display(value)


@register.filter
def discharge_summary_display(value: str) -> str:
    match value:
        case ClassChoices.imp.value | ClassChoices.emer.value:
            return "Discharge Summary"
        case ClassChoices.amb.value:
            return "Outpatient Summary"
        case ClassChoices.hh.value:
            return "Home Health Summary"
        case ClassChoices.vr.value:
            return "Virtual Care Summary"
        case ClassChoices.obsenc.value:
            return "Observation Summary"
        case _:
            return "Patient Summary"


@register.filter
def discharge_disposition_display(value: str) -> str:
    return get_discharge_disposition_display(value)


@register.filter
def observation_value_display(observation: Observation) -> str | None:
    if observation.value.get("display", None):
        return observation.value.get("display", None)
    if observation.value.get("unit", None):
        unit: str = observation.value.get("unit", {}).get("display", None)
        value: float | None = observation.value.get("value", None)
        value = int(value) if value and value.is_integer() else value
        return f"{value} {unit}" if unit else value
    return observation.value.get("value", None)


@register.filter
def medication_dosage_display(medication: MedicationRequest) -> str:
    try:
        dosage = medication.dosage_instruction[0]
        # Prefer text if available
        if dosage.get("text"):
            return dosage["text"]
        dose_val = dosage.get("dose_and_rate", {}).get("dose_quantity", {}).get("value")
        dose_unit = (
            dosage.get("dose_and_rate", {})
            .get("dose_quantity", {})
            .get("unit", {})
            .get("display", "")
        )
        timing = dosage.get("timing", {})
        timing_display = timing.get("code", {}).get("display")
        repeat = timing.get("repeat", {})
        freq = repeat.get("frequency")
        period = repeat.get("period")
        period_unit = repeat.get("period_unit")
        duration = repeat.get("bounds_duration", {}).get("value")
        duration_unit = repeat.get("bounds_duration", {}).get("unit")
        # Build readable string
        parts = []
        if dose_val and dose_unit:
            parts.append(f"Take {dose_val} {dose_unit}")
        if timing_display:
            parts.append(f"{timing_display}")
        elif freq and period and period_unit:
            parts.append(f"every {period} {period_unit}")
        if duration and duration_unit:
            parts.append(f"for {duration} {duration_unit}")
        return " ".join(parts) if parts else None
    except Exception:
        return None
