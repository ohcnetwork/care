from pydantic import BaseModel, Field

from care.action_evaluator.context_engine.contexts.core import (
    EncounterQuestionnaireContext,
)
from care.action_evaluator.instruction_engine.base import (
    BaseInstruction,
    InstructionType,
)
from care.emr.registries.actions.instruction import ActionInstructionRegistry


class ShowMessageInput(BaseModel):
    message: str = Field(
        title="Message",
        description=(
            "Shown to the person who submitted the form. "
            "Insert answers to include them in the text."
        ),
    )


class ShowMessageOutput(BaseModel):
    message: str


class ShowMessageInstruction(BaseInstruction):
    """Surface a message to the submitter — the NOTIFY instruction the
    questionnaire studio offers as "Show a message"."""

    slug = "show_message"
    context = EncounterQuestionnaireContext
    instruction_type = InstructionType.NOTIFY
    input_schema = ShowMessageInput
    output_schema = ShowMessageOutput

    def evaluate(self):
        return {"message": str(self.inputs.get("message", ""))}

    @classmethod
    def authorize(cls, request, user, params: dict) -> bool:
        return True


ActionInstructionRegistry.register(ShowMessageInstruction)
