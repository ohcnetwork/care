from care.action_evaluator.context_engine.base import ActionContextBase
from care.emr.registries.actions.context import ActionContextRegistry


class AppointmentContext(ActionContextBase):
    context_type = "Appointment"


class PatientContext(ActionContextBase):
    context_type = "Patient"


ActionContextRegistry.register(AppointmentContext)
ActionContextRegistry.register(PatientContext)
