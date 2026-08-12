# A lazy context engine that can get data for a given instruction or condition.
# The Instruction engine can layout how the instruction should be evaluated and maintained.
# The Action Evaluator should orchestrate the context engine and Instruction engine to give an output back.


"""
For every context variable, we call the context engine to get the value.
The context engine will get a cache which it can use to avoid re-calculating anything.
"""

from evalidate import EvalException, Expr, base_eval_model
from pydantic import BaseModel, field_validator

from care.action_evaluator.context_engine.evaluator import ActionContextEvaluator
from care.action_evaluator.utils import get_all_variables
from care.emr.registries.actions.instruction import ActionInstructionRegistry

expression_model = base_eval_model.clone()
expression_model.nodes.append("JoinedStr")
expression_model.nodes.append("FormattedValue")
expression_model.nodes.append("Mult")


class Instruction(BaseModel):
    slug: str
    params: dict
    context: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, slug: str) -> str:
        if slug.startswith("i_"):
            raise ValueError("Slugs starting with 'i_' are reserved for internal use")
        return slug


class Action(BaseModel):
    condition: str
    instructions: list[Instruction] = []


class ActionEvaluator:
    def __init__(
        self,
        request,
        user,
        context_type,
        context_obj,
        actions: list[Action],
        field_cache=None,
    ) -> None:
        self.request = request
        self.user = user
        self.context_obj = context_obj
        self.context_type = context_type
        self.actions = [Action.model_validate(x) for x in actions]
        self.field_cache = field_cache or {}
        self.context_cache = {"self": context_obj}
        self.cache = {}

    def evaluate_field(self, field, context_mode: bool = False):
        for variable in get_all_variables(field):
            if field == "self":
                continue
            self.evaluate_context(variable, context_mode)

    def evaluate_context(self, field, context_mode: bool = False):
        if field.startswith(("i_", "q_")):
            return
        ActionContextEvaluator(
            self.request, self.user, self.field_cache, self.context_cache, self.cache
        ).evaluate(
            field,
            self.context_type,
            self.context_obj,
            context_mode,
        )

    def evaluate_condition(self, condition: str):
        variables = get_all_variables(condition)
        for variable in variables:
            if variable not in self.field_cache:
                self.evaluate_context(variable)
        try:
            return bool(
                Expr(condition.strip(), model=expression_model).eval(self.field_cache)
            )
        except EvalException as e:
            raise ValueError(e) from e

    def evaluate(self):
        results = []
        for action in self.actions:
            if action.condition and self.evaluate_condition(action.condition):
                for instruction in action.instructions:
                    outputs = self.evaluate_instruction(instruction)
                    results.append(outputs)
        return results

    def evaluate_instruction(self, instruction: Instruction):
        instruction_context = instruction.context
        self.evaluate_field(instruction_context, context_mode=True)
        context = self.context_cache[instruction_context]
        for field, value in instruction.params.items():
            if (
                isinstance(value, str)
                and value.startswith("{{")
                and value.endswith("}}")
            ):
                field_name = value[2:-2]
                self.evaluate_field(field_name)
                instruction.params[field] = Expr(
                    field_name.strip(), model=expression_model
                ).eval(self.field_cache)
        instruction_class = ActionInstructionRegistry.get_instruction(instruction.slug)
        if not instruction_class:
            err = f"Instruction {instruction.slug} not found"
            raise ValueError(err)
        instruction_instance = instruction_class(
            self.request,
            self.user,
            context,
            instruction.params,
            self.field_cache,
            self.cache,
        )
        return instruction_instance.do_evaluate()


"""
- Clean up all the files and move registries to where they belong
- Action Center Design ( Random Actions as Well ) and Caching
- Authorization for Actions
- Questionnaire Actions
- Action output Dependencies
"""
