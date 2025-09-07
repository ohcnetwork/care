class EvaluationMetricBase:
    context = None
    name = None
    allowed_operations = None

    def __init__(self, context_object):
        self._value = None
        self.context_object = context_object

    @classmethod
    def validate_rule(cls, operation, value):
        if operation not in cls.allowed_operations:
            raise ValueError("Invalid operation")
        # TODO Check if value is the correct type for the operation

    def apply_rule(self, operation, rule):
        if operation not in self.allowed_operations or not getattr(
            self, f"evaluate_{operation}", None
        ):
            raise ValueError("Invalid operation")
        return getattr(self, f"evaluate_{operation}")(rule)

    def evaluate_equality(self, rule):
        value = self.get_value()
        return value == rule

    def evaluate_in_range(self, rule):
        value = self.get_value()
        return value >= rule["min"] and value <= rule["max"]

    def evaluate_intersects_any(self, rule):
        value = self.get_value()
        return value in rule["values"]

    def get_value(self):
        return self._value
