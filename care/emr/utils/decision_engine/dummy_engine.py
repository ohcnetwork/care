from collections.abc import Callable
from typing import Any

from care.emr.utils.decision_engine.base import AbstractConditionEvaluator


class DummyExtendedEvaluator(AbstractConditionEvaluator):
    """
    A dummy subclass of AbstractConditionEvaluator that demonstrates how to extend
    the maps by adding a new condition, a new handler, and a new validator.
    This follows the patterns explained:
    - Adding a new condition ("dummy_status") mapped to an existing handler ("equality").
    - Adding a new handler ("dummy_greater_than") with its function.
    - Adding a new validator for the new handler.
    - Also adding another condition ("dummy_threshold") that uses the new handler.
    Comments inline explain each part.
    """

    def __init__(self, rules: list[dict]):
        super().__init__(rules)
        # In a real subclass, you might add extra init logic if needed

    # Example: Adding a new handler function (dummy_greater_than)
    # This is a private method that will be used in the handler_map
    def _handle_dummy_greater_than(
        self, actual_value: Any, expected_value: Any
    ) -> bool:
        """
        Dummy handler: Checks if actual_value > expected_value.
        """
        return actual_value > expected_value

    @property
    def handler_map(self) -> dict[str, Callable[[Any, Any], bool]]:
        """
        Override to add a new handler.
        Inherits base handlers and adds 'dummy_greater_than'.
        """
        base_map = (
            super().handler_map
        )  # Inherit base handlers (e.g., equality, range, etc.)
        return {
            **base_map,
            "dummy_greater_than": self._handle_dummy_greater_than,  # New handler
        }

    @property
    def validator_map(self) -> dict[str, Callable[[Any], bool]]:
        """
        Override to add a new validator for the new handler.
        Inherits base validators and adds one for 'dummy_greater_than'.
        """
        base_map = super().validator_map  # Inherit base validators
        return {
            **base_map,
            "dummy_greater_than": lambda expected_value: isinstance(
                expected_value, (int, float)
            ),  # New validator
        }

    @property
    def condition_map(self) -> dict[str, str]:
        """
        Override to add new conditions.
        Inherits base conditions (if any) and adds:
        - "dummy_status" using the existing "equality" handler.
        - "dummy_threshold" using the new "dummy_greater_than" handler.
        Optionally, you could override existing conditions if needed.
        """
        base_map = super().condition_map  # Optionally inherit base conditions
        return {
            **base_map,
            "dummy_status": "equality",  # New condition using existing handler
            "dummy_threshold": "dummy_greater_than",  # New condition using new handler
            # Example of overriding: "gender": "equality",  # If base had "gender", this overrides
        }

    # Dummy implementations for abstract methods (required to make the class concrete)
    def evaluate(self, context: dict, value: Any, **kwargs) -> Any:
        """
        Dummy evaluate: In a real subclass, this would use matches_conditions, apply_rule, etc.
        """
        return "dummy_result"

    def handle_no_match(self) -> Any:
        """
        Dummy no-match handler.
        """
        return "no_match"

    def apply_rule(self, rule: dict, value: Any, **kwargs) -> Any:
        """
        Dummy rule application.
        """
        return "applied_rule"
