from care.action_evaluator.context_engine.base import StaticActionContextBase
from care.action_evaluator.context_engine.contexts.core import EncounterContext
from care.emr.registries.actions.field import ActionFieldRegistry

# Encounter values: the enum strings the encounter spec stores
# (`StatusChoices`, `ClassChoices`, `EncounterPriorityChoices`), so a
# condition compares against the same literals the API uses.


class EncounterStatusContext(StaticActionContextBase):
    context_type = EncounterContext
    field = "status"

    def get_context_value(self):
        return self.context_obj.status


class EncounterClassContext(StaticActionContextBase):
    context_type = EncounterContext
    field = "encounter_class"

    def get_context_value(self):
        return self.context_obj.encounter_class


class EncounterPriorityContext(StaticActionContextBase):
    context_type = EncounterContext
    field = "priority"

    def get_context_value(self):
        return self.context_obj.priority


ActionFieldRegistry.register(EncounterStatusContext)
ActionFieldRegistry.register(EncounterClassContext)
ActionFieldRegistry.register(EncounterPriorityContext)
