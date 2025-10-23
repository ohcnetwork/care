from pydantic import BaseModel, model_validator

from care.utils.registries.evaluation_metric import EvaluatorMetricsRegistry


class EvaluatorConditionSpec(BaseModel):
    metric: str
    operation: str
    value: dict | str

    @model_validator(mode="after")
    def validate_condition(self):
        evaluator = EvaluatorMetricsRegistry.get_evaluator(self.metric)
        if not evaluator:
            raise ValueError("Invalid metric")
        evaluator.validate_rule(self.operation, self.value)
        return self
