"""
What an instruction acts on. `instruction.context` is a dotted path the
evaluator resolves before the instruction runs: `self` is the raw object the
action fires for (a `QuestionnaireResponse` for questionnaire actions, a
`TokenBooking` for appointments), anything else is a registered context
wrapper (`PatientContext`, `EncounterContext`) around the model. These
helpers accept either, so an instruction works whether the author pointed
it at the neighbour or left it on the submission itself.
"""

from care.action_evaluator.context_engine.base import ActionContextBase
from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient


def _unwrap(context):
    if isinstance(context, ActionContextBase):
        return context.context_obj
    return context


def resolve_encounter(context) -> Encounter | None:
    obj = _unwrap(context)
    if isinstance(obj, Encounter):
        return obj
    encounter = getattr(obj, "encounter", None)
    return encounter if isinstance(encounter, Encounter) else None


def resolve_patient(context) -> Patient | None:
    obj = _unwrap(context)
    if isinstance(obj, Patient):
        return obj
    patient = getattr(obj, "patient", None)
    return patient if isinstance(patient, Patient) else None
