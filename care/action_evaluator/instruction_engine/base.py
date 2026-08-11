from pydantic import BaseModel

from care.action_evaluator.context_engine.base import (
    ActionContextBase,
)


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
        return self.evaluate()
        # outputs = self.evaluate()
        # return self.output_schema.model_validate(outputs, context=self.context)

    def authorize(self) -> bool:
        raise NotImplementedError("Subclasses must implement this method")
