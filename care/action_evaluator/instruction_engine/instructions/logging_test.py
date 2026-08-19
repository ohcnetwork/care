from care.action_evaluator.context_engine.contexts.core import AppointmentContext
from care.action_evaluator.instruction_engine.base import (
    BaseInstruction,
    InstructionType,
)
from care.emr.registries.actions.instruction import ActionInstructionRegistry


class LoggingActionInstruction(BaseInstruction):
    slug = "logging"
    context = AppointmentContext
    instruction_type = InstructionType.NOTIFY

    def evaluate(self):
        import logging

        logging.info(f"Logging Action Instruction: {self.inputs}")  # noqa : LOG015 G004
        return self.inputs

    @classmethod
    def authorize(cls, request, user, params: dict) -> bool:
        return True


ActionInstructionRegistry.register(LoggingActionInstruction)
