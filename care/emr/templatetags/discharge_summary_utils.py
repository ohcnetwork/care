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
        return medication.dosage_instruction[0]["text"]
    except (IndexError, KeyError, TypeError):
        return None
