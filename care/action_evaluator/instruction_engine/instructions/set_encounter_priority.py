from pydantic import BaseModel, Field
from rest_framework.exceptions import ValidationError

from care.action_evaluator.context_engine.contexts.core import EncounterContext
from care.action_evaluator.instruction_engine.base import (
    BaseInstruction,
    InstructionType,
)
from care.action_evaluator.instruction_engine.resolvers import resolve_encounter
from care.emr.registries.actions.instruction import ActionInstructionRegistry
from care.emr.resources.encounter.constants import EncounterPriorityChoices

# Imported from `EMRConfig.ready()`: the authorization controller drags the
# resource-spec graph in and would circle back into a half-imported spec
# module (see tag_resource.py), so it is imported where it is used.


class SetEncounterPriorityInput(BaseModel):
    priority: EncounterPriorityChoices = Field(
        title="Priority",
        description="The priority the encounter is moved to.",
    )


class SetEncounterPriorityOutput(BaseModel):
    performed: bool
    priority: str | None = None
    message: str


class SetEncounterPriorityInstruction(BaseInstruction):
    """Move the encounter to a priority when the condition holds — e.g. a
    triage form that escalates on a high temperature."""

    slug = "set_encounter_priority"
    context = EncounterContext
    instruction_type = InstructionType.PERFORMED
    input_schema = SetEncounterPriorityInput
    output_schema = SetEncounterPriorityOutput

    def evaluate(self):
        priority = EncounterPriorityChoices(self.inputs["priority"]).value
        encounter = resolve_encounter(self.context)
        if encounter is None:
            return {
                "performed": False,
                "priority": None,
                "message": "This form is not attached to an encounter",
            }
        from care.security.authorization import AuthorizationController

        if not AuthorizationController.call(
            "can_update_encounter_obj", self.user, encounter
        ):
            return {
                "performed": False,
                "priority": encounter.priority,
                "message": "Not permitted to change the encounter priority",
            }
        if encounter.priority == priority:
            return {
                "performed": False,
                "priority": priority,
                "message": f"Encounter priority is already {priority}",
            }
        encounter.priority = priority
        encounter.save(update_fields=["priority", "modified_date"])
        return {
            "performed": True,
            "priority": priority,
            "message": f"Encounter priority set to {priority}",
        }

    @classmethod
    def authorize(cls, request, user, params: dict) -> bool:
        try:
            EncounterPriorityChoices(params.get("priority"))
        except ValueError as e:
            err = f"Unknown encounter priority {params.get('priority')!r}"
            raise ValidationError(err) from e
        return True


ActionInstructionRegistry.register(SetEncounterPriorityInstruction)
