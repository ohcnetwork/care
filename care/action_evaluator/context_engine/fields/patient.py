from care.action_evaluator.context_engine.base import (
    DynamicActionContextBase,
    StaticActionContextBase,
)
from care.action_evaluator.context_engine.contexts.core import (
    AppointmentContext,
    EncounterQuestionnaireContext,
    PatientContext,
)
from care.emr.registries.actions.field import ActionFieldRegistry


class TestContext1(DynamicActionContextBase):
    context_type = AppointmentContext

    def get_context_value(self, field):
        return "test1234"


class PatientAgeContext(StaticActionContextBase):
    context_type = PatientContext
    field = "age"

    def get_context_value(self):
        return self.context_obj.age


class AppointmentPatientContext(StaticActionContextBase):
    context_type = AppointmentContext
    field = "patient"
    target_context_type = PatientContext

    def get_context_value(self):
        return PatientContext(self.context_obj.patient)


class EncounterQuestionnairePatientContext(StaticActionContextBase):
    context_type = EncounterQuestionnaireContext
    field = "patient"
    target_context_type = PatientContext

    def get_context_value(self):
        return PatientContext(self.context_obj.patient)


ActionFieldRegistry.register(TestContext1)
ActionFieldRegistry.register(PatientAgeContext)
ActionFieldRegistry.register(AppointmentPatientContext)
ActionFieldRegistry.register(EncounterQuestionnairePatientContext)
