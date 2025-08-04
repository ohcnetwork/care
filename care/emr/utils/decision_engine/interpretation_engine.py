from typing import Any

from care.emr.utils.decision_engine.base import AbstractRuleEngine


class InterpretationEngine(AbstractRuleEngine):
    """An interpretation engine that evaluates values against rules to determine interpretations."""

    def register_internal_conditions(self):
        """Register internal condition mappings for interpretation."""
        conditions = {
            "gender": "equality",
            "age": "range",
            "applies_to": "in_or_equality",
        }
        for key, handler_name in conditions.items():
            if key not in self._condition_registry:
                self._condition_registry[key] = handler_name

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

        if range_spec.get("values") is not None:
            return value in range_spec["values"]

        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                return False

        min_val = range_spec.get("min")
        max_val = range_spec.get("max")

        if max_val is None:
            return value > (min_val or 0)
        if min_val is None:
            return value < (max_val or float("inf"))
        return min_val <= value <= max_val

    def evaluate(self, context: dict, value: Any, **kwargs) -> Any:
        """Evaluate the context and value to find the first matching rule and apply it for interpretation."""
        rules_to_check = self.rules
        for rule in rules_to_check:
            if self.matches_conditions(rule.get("conditions", {}), context):
                return self.apply_rule(rule, value, **kwargs)
        return self.handle_no_match()
