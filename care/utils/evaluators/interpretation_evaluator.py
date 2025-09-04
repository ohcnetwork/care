from datetime import datetime
from typing import Any

from care.utils.evaluators.base import AbstractEvaluator


class InterpretationEvaluator(AbstractEvaluator):
    """
    An evaluator that determines clinical interpretations for observation values.
    """

    @property
    def condition_map(self) -> dict[str, str]:
        """
        Mapping of condition keys to handler names for interpretation evaluation.
        """
        return {
            "gender": "equality",
            "age": "range",
            "applies_to": "intersects_any",
        }

    def handle_no_match(self) -> str:
        """
        Return the fallback interpretation when no rules match the given context.
        """
        return "undetermined"

    def apply_rule(self, rule: dict, value: Any, **kwargs) -> str:
        """
        Apply a matched rule to determine the clinical interpretation of a value.
        """
        # Determine if we're dealing with numeric or coded data
        has_ranges = bool(rule.get("ranges", []))
        has_coded_values = bool(
            rule.get("normal_coded_value_set", [])
            or rule.get("critical_coded_value_set", [])
            or rule.get("abnormal_coded_value_set", [])
        )

        if has_ranges:
            for r in rule.get("ranges", []):
                if self.value_fits(value, r):
                    return r["interpretation"]
        elif has_coded_values:
            extracted_value = self.extract_value(value)

            for normal_code in rule.get("normal_coded_value_set", []):
                if self._matches_coded_value(extracted_value, normal_code):
                    return "normal"

            for critical_code in rule.get("critical_coded_value_set", []):
                if self._matches_coded_value(extracted_value, critical_code):
                    return "critical"

            for abnormal_code in rule.get("abnormal_coded_value_set", []):
                if self._matches_coded_value(extracted_value, abnormal_code):
                    return "abnormal"

        return self.handle_no_match()

    def _matches_coded_value(self, value: Any, coded_value: dict) -> bool:
        """
        Check if an extracted value matches a coded value from a valueset.
        """
        if isinstance(coded_value, dict):
            code = coded_value.get("code")
            if code and str(value) == str(code):
                return True
        return False

    def value_fits(self, value: Any, range_spec: dict) -> bool:
        """
        Check if an observation value fits within the given range specification.
        """
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

    def evaluate(self, context: dict, value: Any, **kwargs) -> str:
        """
        Evaluate an observation value against rules to determine clinical interpretation.
        """
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

    def _get_required_context_keys(self) -> set[str]:
        """
        Analyze rules to determine which context keys are required for evaluation.
        """
        required_keys = set()
        for rule in self.rules:
            conditions = rule.get("conditions", {})
            required_keys.update(conditions.keys())
        return required_keys

    def build_patient_context(self, patient, effective_datetime: str) -> dict:
        """
        Build context dictionary with only the required patient data for evaluation.
        """
        required_keys = self._get_required_context_keys()
        context = {}

        if "gender" in required_keys:
            context["gender"] = patient.gender

        if "age" in required_keys:
            date_delta = (
                datetime.fromisoformat(effective_datetime).date()
                - patient.date_of_birth
            )
            context["age"] = date_delta.days / 365.25

        if "applies_to" in required_keys:
            from care.emr.tagging.base import (
                PatientFacilityTagManager,
                PatientInstanceTagManager,
            )

            # Get patient instance tags
            instance_tags = [
                tag.get("slug")
                for tag in PatientInstanceTagManager().render_tags(patient)
                if tag.get("slug") is not None
            ]

            # Get patient facility tags
            facility_tags = []
            if patient.facility:
                facility_tags = [
                    tag.get("slug")
                    for tag in PatientFacilityTagManager(patient.facility).render_tags(
                        patient
                    )
                    if tag.get("slug") is not None
                ]

            context["applies_to"] = instance_tags + facility_tags

        return context

    def _get_reference_range(
        self, matched_condition: dict | None, interpretation: str
    ) -> list:
        """
        Extract reference ranges from a matched rule condition.
        """
        if not matched_condition:
            return []

        # For numeric data, return the numeric ranges
        numeric_ranges = matched_condition.get("ranges", [])
        if numeric_ranges:
            return numeric_ranges
        return []

    def extract_value(self, val: Any) -> Any:
        """
        Extract the core value from complex observation value structures.
        """
        if isinstance(val, dict):
            if coding := val.get("coding"):
                return coding.get("code")
            if "quantity" in val:
                return val["quantity"]
            if "value" in val:
                return val["value"]
        return val
