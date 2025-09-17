from typing import Any

from care.emr.models.valueset import ValueSet
from care.emr.resources.observation_definition.spec import (
    ABNORMAL_INTERPRETATION,
    CRITICAL_INTERPRETATION,
    NORMAL_INTERPRETATION,
)
from care.utils.registries.evaluation_metric import EvaluatorMetricsRegistry


class InterpretationEvaluator:
    def __init__(self, rules: list[dict], metric_cache=None):
        self.rules = rules
        if metric_cache:
            self.metric_cache = metric_cache
        else:
            self.metric_cache = {}

    def check_valueset(self, valueset, code, interpretation):
        valueset = ValueSet.objects.get(slug=valueset)
        lookup = valueset.lookup(code)
        if lookup:
            return interpretation
        return False

    def get_interpretation(self, rule: dict, value: Any):  # noqa PLR0911 PLR0912
        """
        Find the interpretation given the set of rules.
        """
        if rule.get("ranges"):
            if isinstance(value, dict):
                if "coding" in value and value["coding"] is not None:
                    raise ValueError("Coding not supported")
                if "quantity" in value:
                    value = value["quantity"]
                elif "value" in value:
                    value = value["value"]
                else:
                    return False, False

            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    return False, False
            for value_range in rule.get("ranges", []):
                min_val = value_range.get("min")
                max_val = value_range.get("max")

                if min_val is None and max_val is None:
                    raise ValueError("Min and max cannot be None")
                if min_val is None:
                    min_val = float("-inf")
                if max_val is None:
                    max_val = float("inf")

                if min_val <= value <= max_val:
                    return value_range.get("interpretation"), rule.get("ranges", [])
        else:
            # Handle Valueset based interpretation
            if "coding" not in value:
                raise ValueError("Coding not found")
            if rule.get("normal_coded_value_set"):
                interpretation = self.check_valueset(
                    rule.get("normal_coded_value_set"),
                    value.get("coding"),
                    NORMAL_INTERPRETATION,
                )
                if interpretation:
                    return interpretation, []
            if rule.get("critical_coded_value_set"):
                interpretation = self.check_valueset(
                    rule.get("critical_coded_value_set"),
                    value.get("coding"),
                    CRITICAL_INTERPRETATION,
                )
                if interpretation:
                    return interpretation, []
            if rule.get("abnormal_coded_value_set"):
                interpretation = self.check_valueset(
                    rule.get("abnormal_coded_value_set"),
                    value.get("coding"),
                    ABNORMAL_INTERPRETATION,
                )
                if interpretation:
                    return interpretation, []
            for valueset_interpretation in rule.get("valueset_interpretation", []):
                if not valueset_interpretation.get("valuset"):
                    continue
                interpretation = self.check_valueset(
                    valueset_interpretation.get("valuset"),
                    value.get("coding"),
                    valueset_interpretation.get("interpretation"),
                )
                if interpretation:
                    return interpretation, []

        return False, False

    def evaluate_conditions(self, conditions, context):
        if not conditions:
            return True
        for condition in conditions:
            metric = condition.get("metric")
            if metric in self.metric_cache:
                metric_evaluator_obj = self.metric_cache[metric]
            else:
                metric_evaluator = EvaluatorMetricsRegistry.get_evaluator(metric)
                metric_evaluator_obj = metric_evaluator(
                    context.get(metric_evaluator.context)
                )
                self.metric_cache[metric] = metric_evaluator_obj
            if metric_evaluator_obj.apply_rule(
                condition.get("operation"), condition.get("value")
            ):
                return True
        return False

    def get_matching_condition(self, context: dict, value: Any):
        for rule in self.rules:
            conditions = rule.get("conditions", {})
            if self.evaluate_conditions(conditions, context):
                return rule, value
        return None, None

    def evaluate(self, context: dict, value: Any) -> str:
        """
        Evaluate an observation value against rules to determine clinical interpretation.
        """
        rule, value = self.get_matching_condition(context, value)
        # All required conditions are met.
        if rule:
            interpretation, ranges = self.get_interpretation(rule, value)
            if interpretation:
                return interpretation, ranges
        return None, []
