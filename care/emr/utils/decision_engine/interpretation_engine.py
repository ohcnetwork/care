from typing import Any

from care.emr.utils.decision_engine.base import AbstractConditionEvaluator


class InterpretationEvaluator(AbstractConditionEvaluator):
    """An evaluator that determines interpretations based on rules and values."""

    @property
    def condition_map(self) -> dict[str, str]:
        """
        Mapping of condition keys to handler names specific to interpretation.
        """
        return {
            "gender": "equality",
            "age": "range",
            "applies_to": "intersects_any",
        }

    def handle_no_match(self) -> str:
        """Return the fallback interpretation if no rule matches."""
        return "undetermined"

    def apply_rule(self, rule: dict, value: Any, **kwargs) -> str:
        """Apply the matched rule to compute the interpretation for the given value."""
        for r in rule.get("ranges", []):
            if self.value_fits(value, r):
                return r["interpretation"]
        return self.handle_no_match()

    def value_fits(self, value, range_spec):
        """Check if the value fits within the given range specification."""
        if isinstance(value, dict):
            if "coding" in value and value["coding"] is not None:
                value = value["coding"].get("code")
            elif "quantity" in value:
                value = value["quantity"]
            elif "value" in value:
                value = value["value"]
            else:
                return False

        if range_spec.get("value") is not None:
            return value == range_spec["value"]

        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                return False

        min_val = range_spec.get("min")
        max_val = range_spec.get("max")

        if min_val is None:
            min_val = float("-inf")
        if max_val is None:
            max_val = float("inf")

        return min_val <= value <= max_val

    def evaluate(self, context: dict, value: Any, **kwargs) -> Any:
        """Evaluate the context and value to find the first matching rule and apply it for interpretation."""
        for rule in self.rules:
            if self.matches_conditions(rule.get("conditions", {}), context):
                return self.apply_rule(rule, value, **kwargs)
        return self.handle_no_match()

    def get_matching_condition(self, context: dict) -> dict | None:
        """
        Find the first rule that matches the given context conditions.
        """
        for rule in self.rules:
            if self.matches_conditions(rule.get("conditions", {}), context):
                return rule
        return None
