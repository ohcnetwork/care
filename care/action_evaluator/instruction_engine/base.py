from enum import Enum

from pydantic import BaseModel

from care.action_evaluator.context_engine.base import (
    ActionContextBase,
)


class InstructionType(str, Enum):
    REDIRECT = "REDIRECT"
    PERFORMED = "PERFORMED"
    NOTIFY = "NOTIFY"
    TEXT = "TEXT"


class BaseInstruction:
    slug: str
    input_schema: BaseModel
    output_schema: BaseModel
    context: ActionContextBase

    def clean_inputs(self, inputs: dict) -> dict:
        return inputs

    def __init__(self, request, user, context, inputs, field_cache, cache):
        self.request = request
        self.user = user
        self.inputs = self.clean_inputs(inputs)
        self.context = context
        # self.input_instance = self.input_schema.model_validate(
        #     self.inputs,
        #     context=self.context,
        # )
        self.field_cache = field_cache
        self.cache = cache

    def evaluate(self) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

    def do_evaluate(self):
        results = self.evaluate()
        return {
            "slug": self.slug,
            "instruction_type": self.instruction_type,
            "results": results,
        }

    def authorize(self) -> bool:
        raise NotImplementedError("Subclasses must implement this method")
