from collections.abc import Callable
from typing import Any


class AbstractRuleEngine:
    """
    An abstract base class for rule engines that evaluate conditions using registered handlers and validators.
    """

    _handler_registry: dict[
        str, Callable[[Any, Any], bool]
    ] = {}  # handler_name -> evaluation func
    _validator_registry: dict[
        str, Callable[[Any], bool]
    ] = {}  # handler_name -> validation func
    _condition_registry: dict[str, str] = {}  # condition_key -> handler_name

    def _register_internal_handlers(self):
        """
        Register default handler functions for condition evaluation.

        This method registers built-in handlers like equality, range, in_or_equality, and in.
        It ensures handlers are only added if not already present.
        """
        handlers = {
            "equality": self._handle_equality,
            "range": self._handle_range,
            "in_or_equality": self._handle_in_or_equality,
            "in": self._handle_in,
        }
        for name, func in handlers.items():
            if name not in self._handler_registry:
                self._handler_registry[name] = func

    def _register_internal_validators(self):
        """
        Register default validator functions for condition specs.

        This method registers built-in validators corresponding to the internal handlers.
        It ensures validators are only added if not already present.
        """
        validators = {
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
        }
        for name, func in validators.items():
            if name not in self._validator_registry:
                self._validator_registry[name] = func

    def register_internal_conditions(self):
        """
        Register internal condition mappings (e.g., gender to equality).

        Raises:
            NotImplementedError: Subclasses must implement this method to define internal condition mappings.
        """
        raise NotImplementedError(
            "Subclasses must implement register_internal_conditions"
        )

    @classmethod
    def register_external_handler(cls, name: str, handler: Callable[[Any, Any], bool]):
        """
        Register an external handler function (e.g., from plugin). Verify before adding.

        Args:
            name (str): The name of the handler.
            handler (Callable[[Any, Any], bool]): The handler function to register.

        Raises:
            ValueError: If the name is invalid, handler is not callable, or name is already registered.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Handler name must be a non-empty string.")
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        if name in cls._handler_registry:
            err = f"Handler '{name}' already registered."
            raise ValueError(err)
        cls._handler_registry[name] = handler

    @classmethod
    def register_external_validator(cls, name: str, validator: Callable[[Any], bool]):
        """
        Register an external validator function (e.g., from plugin). Verify before adding.

        Args:
            name (str): The name of the validator.
            validator (Callable[[Any], bool]): The validator function to register.

        Raises:
            ValueError: If the name is invalid, validator is not callable, or name is already registered.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Validator name must be a non-empty string.")
        if not callable(validator):
            raise ValueError("Validator must be a callable function.")
        if name in cls._validator_registry:
            err = f"Validator '{name}' already registered."
            raise ValueError(err)
        cls._validator_registry[name] = validator

    @classmethod
    def register_external_condition(cls, name: str, handler_name: str):
        """
        Register an external condition mapping to a handler (e.g., from plugin). Verify before adding.

        Args:
            name (str): The name of the condition.
            handler_name (str): The name of the associated handler.

        Raises:
            ValueError: If the name is invalid, condition is already registered, or handler is not found.
        """
        if not isinstance(name, str) or not name:
            err = f"Condition name '{name}' must be a non-empty string."
            raise ValueError(err)
        if name in cls._condition_registry:
            err = f"Condition '{name}' already registered."
            raise ValueError(err)
        if handler_name not in cls._handler_registry:
            err = f"Handler '{handler_name}' not found in registry."
            raise ValueError(err)
        cls._condition_registry[name] = handler_name

    def __init__(self, rules: list[dict]):
        """
        Initialize with a list of rules (e.g., qualified_ranges).

        This constructor registers internal handlers, validators, and conditions.

        Args:
            rules (list[dict]): The list of rules to be used for evaluation.
        """
        self._register_internal_handlers()
        self._register_internal_validators()
        self.register_internal_conditions()
        self.handler_registry = self._handler_registry
        self.validator_registry = self._validator_registry
        self.condition_registry = self._condition_registry
        self.rules = rules

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

    def matches_conditions(self, conditions: dict, context: dict) -> bool:
        """
        Check if all conditions match the context using registered handlers.

        Args:
            conditions (dict): Dictionary of conditions (key: condition_key, value: expected_value).
            context (dict): Dictionary providing actual values for evaluation.

        Returns:
            bool: True if all conditions match, False otherwise.
        """
        for key, expected_value in conditions.items():
            handler_name = self.condition_registry.get(key)
            if not handler_name:
                return False
            handler = self.handler_registry.get(handler_name)
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
        Validate condition specs using registered validators.

        Args:
            conditions (dict): Dictionary of conditions to validate.

        Returns:
            bool: True if all conditions are valid, False otherwise.
        """
        for key, expected_value in conditions.items():
            handler_name = self.condition_registry.get(key)
            if not handler_name:
                return False
            validator = self.validator_registry.get(handler_name)
            if not validator:
                return False
            try:
                if not validator(expected_value):
                    return False
            except Exception:
                return False
        return True

    def evaluate(self, context: dict, value: Any, **kwargs) -> Any:
        """
        Evaluate the rules against the provided context and value.

        Args:
            context (dict): Context for condition matching.
            value (Any): The value to apply rules to.
            **kwargs: Additional keyword arguments for evaluation.

        Raises:
            NotImplementedError: Subclasses must implement this method.

        Returns:
            Any: The result of the evaluation.
        """
        raise NotImplementedError("Subclasses must implement evaluate")

    def handle_no_match(self) -> Any:
        """
        Return fallback result if no rule matches.

        Raises:
            NotImplementedError: Subclasses must implement this method.

        Returns:
            Any: The fallback result.
        """
        raise NotImplementedError("Subclasses must implement handle_no_match")

    def apply_rule(self, rule: dict, value: Any, **kwargs) -> Any:
        """
        Apply the matched rule to produce a result.

        Args:
            rule (dict): The matched rule to apply.
            value (Any): The value to process.
            **kwargs: Additional keyword arguments for rule application.

        Raises:
            NotImplementedError: Subclasses must implement this method.

        Returns:
            Any: The result after applying the rule.
        """
        raise NotImplementedError("Subclasses must implement apply_rule")
