from care.action_evaluator.context_engine.base import ActionContextBase
from care.emr.registries.actions.context import ActionContextRegistry


class AppointmentContext(ActionContextBase):
    context_type = "Appointment"


class PatientContext(ActionContextBase):
    context_type = "Patient"


class EncounterQuestionnaireContext(ActionContextBase):
    context_type = "EncounterQuestionnaire"


class PatientQuestionnaireContext(ActionContextBase):
    context_type = "PatientQuestionnaire"


class EncounterContext(ActionContextBase):
    context_type = "Encounter"


ActionContextRegistry.register(AppointmentContext)
ActionContextRegistry.register(PatientContext)
ActionContextRegistry.register(EncounterQuestionnaireContext)
ActionContextRegistry.register(PatientQuestionnaireContext)
ActionContextRegistry.register(EncounterContext)
