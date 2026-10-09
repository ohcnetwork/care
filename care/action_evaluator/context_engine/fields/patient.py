from care.action_evaluator.context_engine.base import (
    DynamicActionContextBase,
    StaticActionContextBase,
)
from care.action_evaluator.context_engine.contexts.core import (
    AppointmentContext,
    EncounterContext,
    EncounterQuestionnaireContext,
    PatientContext,
    PatientQuestionnaireContext,
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


class PatientQuestionnairePatientContext(StaticActionContextBase):
    context_type = PatientQuestionnaireContext
    field = "patient"
    target_context_type = PatientContext

    def get_context_value(self):
        return PatientContext(self.context_obj.patient)


class EncounterQuestionnaireEncounterContext(StaticActionContextBase):
    context_type = EncounterQuestionnaireContext
    field = "encounter"
    target_context_type = EncounterContext

    def get_context_value(self):
        return EncounterContext(self.context_obj.encounter)


class PatientGenderContext(StaticActionContextBase):
    context_type = PatientContext
    field = "gender"

    def get_context_value(self):
        return self.context_obj.gender


class PatientNameContext(StaticActionContextBase):
    context_type = PatientContext
    field = "name"

    def get_context_value(self):
        return self.context_obj.name


class PatientPhoneNumberContext(StaticActionContextBase):
    context_type = PatientContext
    field = "phone_number"

    def get_context_value(self):
        return self.context_obj.phone_number


class PatientDateOfBirthContext(StaticActionContextBase):
    context_type = PatientContext
    field = "date_of_birth"

    def get_context_value(self):
        date_of_birth = self.context_obj.date_of_birth
        return date_of_birth.isoformat() if date_of_birth else None


class PatientYearOfBirthContext(StaticActionContextBase):
    context_type = PatientContext
    field = "year_of_birth"

    def get_context_value(self):
        return self.context_obj.year_of_birth


class PatientBloodGroupContext(StaticActionContextBase):
    context_type = PatientContext
    field = "blood_group"

    def get_context_value(self):
        return self.context_obj.blood_group


class PatientDeceasedContext(StaticActionContextBase):
    context_type = PatientContext
    field = "deceased"

    def get_context_value(self):
        return self.context_obj.deceased_datetime is not None


ActionFieldRegistry.register(TestContext1)
ActionFieldRegistry.register(PatientAgeContext)
ActionFieldRegistry.register(AppointmentPatientContext)
ActionFieldRegistry.register(EncounterQuestionnairePatientContext)
ActionFieldRegistry.register(PatientQuestionnairePatientContext)
ActionFieldRegistry.register(EncounterQuestionnaireEncounterContext)
ActionFieldRegistry.register(PatientAgeContext)
ActionFieldRegistry.register(PatientGenderContext)
ActionFieldRegistry.register(PatientNameContext)
ActionFieldRegistry.register(PatientPhoneNumberContext)
ActionFieldRegistry.register(PatientDateOfBirthContext)
ActionFieldRegistry.register(PatientYearOfBirthContext)
ActionFieldRegistry.register(PatientBloodGroupContext)
ActionFieldRegistry.register(PatientDeceasedContext)
