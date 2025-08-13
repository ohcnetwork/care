from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class AbstractConditionEvaluator(ABC):
    """
    An abstract base class for evaluating conditions and applying rules.
    """

    def __init__(self, rules: list[dict]):
        """
        Initialize with a list of rules.

        Args:
            rules (list[dict]): The list of rules to be used for evaluation.
        """
        self.rules = rules
        self._validate_maps()

    def _validate_maps(self):
        handlers = set(self.handler_map.keys())
        validators = set(self.validator_map.keys())
        used_handlers = set(self.condition_map.values())

        missing_validators = handlers - validators
        if missing_validators:
            err = f"Missing validators for handlers: {missing_validators}"
            raise ValueError(err)

        missing_handlers = used_handlers - handlers
        if missing_handlers:
            err = f"Missing handlers for handlers: {missing_handlers}"
            raise ValueError(err)

        missing_condition_validators = used_handlers - validators
        if missing_condition_validators:
            err = f"Missing validators for conditions: {missing_condition_validators}"
            raise ValueError(err)

    @property
    def handler_map(self) -> dict[str, Callable[[Any, Any], bool]]:
        """
        Mapping of handler names to their functions.
        Subclasses can override to add or modify handlers.
        """
        return {
            "equality": self._handle_equality,
            "range": self._handle_range,
            "in_or_equality": self._handle_in_or_equality,
            "in": self._handle_in,
            "intersects_any": self._handle_intersects_any,
            "intersects_all": self._handle_intersects_all,
        }

    @property
    def validator_map(self) -> dict[str, Callable[[Any], bool]]:
        """
        Mapping of validator names to their functions.
        Subclasses can override to add or modify validators.
        """
        return {
            "equality": lambda expected_value: isinstance(
                expected_value, (str, int, float)
            ),
            "range": lambda expected_value: isinstance(expected_value, dict)
            and all(
                expected_value.get(key) is None
                or isinstance(expected_value.get(key), (int, float))
                for key in ["min", "max"]
                if key in expected_value
            ),
            "in_or_equality": lambda expected_value: isinstance(
                expected_value, (str, list)
            ),
            "in": lambda expected_value: isinstance(expected_value, list),
            "intersects_any": lambda expected_value: isinstance(
                expected_value, (str, list)
            ),
            "intersects_all": lambda expected_value: isinstance(
                expected_value, (str, list)
            ),
        }

    @property
    def condition_map(self) -> dict[str, str]:
        """
        Mapping of condition keys to handler names.
        Subclasses should override to define their specific conditions.
        """
        return {}

    def _handle_equality(self, actual_value: Any, expected_value: Any) -> bool:
        """
        Check if actual_value equals expected_value.

        Args:
            actual_value (Any): The value from the context.
            expected_value (Any): The expected value for comparison.

        Returns:
            bool: True if values are equal, False otherwise.
        """
        return actual_value == expected_value

    def _handle_range(self, actual_value: Any, expected_value: dict) -> bool:
        """
        Check if actual_value falls within min-max range.

        Args:
            actual_value (Any): The value from the context (expected to be numeric).
            expected_value (dict): Dictionary with 'min' and/or 'max' keys for range bounds.

        Returns:
            bool: True if value is within the range, False otherwise.
        """
        min_v = expected_value.get("min", float("-inf"))
        max_v = expected_value.get("max", float("inf"))
        return min_v <= actual_value <= max_v

    def _handle_in_or_equality(self, actual_value: Any, expected_value: Any) -> bool:
        """
        Check if actual_value is in expected_value (list) or equals it.

        Args:
            actual_value (Any): The value from the context.
            expected_value (Any): The expected value (str or list).

        Returns:
            bool: True if value matches or is in the list, False otherwise.
        """
        if isinstance(expected_value, list):
            return actual_value in expected_value
        return actual_value == expected_value

    def _handle_in(self, actual_value: Any, expected_value: Any) -> bool:
        """
        Check if actual_value is in expected_value (must be list).

        Args:
            actual_value (Any): The value from the context.
            expected_value (Any): The expected list of values.

        Returns:
            bool: True if value is in the list, False otherwise.
        """
        if isinstance(expected_value, list):
            return actual_value in expected_value
        return False

    def _handle_intersects_any(self, actual_value: Any, expected_value: Any) -> bool:
        """
        Check if there is at least one overlap between actual_value and expected_value (OR semantics).
        Treat scalars as single-element lists for flexibility.

        Args:
            actual_value (Any): The value from the context (e.g., list of patient tags).
            expected_value (Any): The expected value from conditions (e.g., list of required tags).

        Returns:
            bool: True if there is at least one common element, False otherwise.
        """
        if not isinstance(actual_value, list):
            actual_value = [actual_value]
        if not isinstance(expected_value, list):
            expected_value = [expected_value]
        return bool(set(actual_value) & set(expected_value))

    def _handle_intersects_all(self, actual_value: Any, expected_value: Any) -> bool:
        """
        Check if all elements in expected_value are present in actual_value (AND semantics).
        Treat scalars as single-element lists for flexibility.

        Args:
            actual_value (Any): The value from the context (e.g., list of patient tags).
            expected_value (Any): The expected value from conditions (e.g., list of required tags).

        Returns:
            bool: True if all expected elements are in actual_value, False otherwise.
        """
        if not isinstance(actual_value, list):
            actual_value = [actual_value]
        if not isinstance(expected_value, list):
            expected_value = [expected_value]
        return set(expected_value).issubset(set(actual_value))

    def matches_conditions(self, conditions: dict, context: dict) -> bool:
        """
        Check if all conditions match the context using mapped handlers.

        Args:
            conditions (dict): Dictionary of conditions (key: condition_key, value: expected_value).
            context (dict): Dictionary providing actual values for evaluation.

        Returns:
            bool: True if all conditions match, False otherwise.
        """
        for key, expected_value in conditions.items():
            handler_name = self.condition_map.get(key)
            if not handler_name:
                return False

            handler = self.handler_map.get(handler_name)
            if not handler:
                return False

            actual_value = context.get(key)
            if actual_value is None:
                return False

            try:
                if not handler(actual_value, expected_value):
                    return False
            except Exception:
                return False
        return True

    def validate_conditions(self, conditions: dict) -> bool:
        """
        Validate condition specs using mapped validators.

        Args:
            conditions (dict): Dictionary of conditions to validate.

        Returns:
            bool: True if all conditions are valid, False otherwise.
        """
        for key, expected_value in conditions.items():
            handler_name = self.condition_map.get(key)
            if not handler_name:
                return False
            validator = self.validator_map.get(handler_name)
            if not validator:
                return False
            try:
                if not validator(expected_value):
                    return False
            except Exception:
                return False
        return True

    @abstractmethod
    def evaluate(self, context: dict, value: Any, **kwargs) -> Any:
        """
        Evaluate the rules against the provided context and value.

        Args:
            context (dict): Context for condition matching.
            value (Any): The value to apply rules to.
            **kwargs: Additional keyword arguments for evaluation.

        Returns:
            Any: The result of the evaluation.
        """

    @abstractmethod
    def handle_no_match(self) -> Any:
        """
        Return fallback result if no rule matches.

        Returns:
            Any: The fallback result.
        """

    @abstractmethod
    def apply_rule(self, rule: dict, value: Any, **kwargs) -> Any:
        """
        Apply the matched rule to produce a result.

        Args:
            rule (dict): The matched rule to apply.
            value (Any): The value to process.
            **kwargs: Additional keyword arguments for rule application.

        Returns:
            Any: The result after applying the rule.
        """
