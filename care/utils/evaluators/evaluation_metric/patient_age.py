from datetime import date

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from pydantic import BaseModel, StrictInt

from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)


class ValueSpec(BaseModel):
    value: StrictInt
    value_type: str = "years"


class RangeSpec(BaseModel):
    min: StrictInt
    max: StrictInt
    value_type: str = "years"


class PatientAgeMetric(EvaluationMetricBase):
    context = "patient"
    name = "patient_age"
    verbose_name = "Patient Age"
    allowed_operations = [
        AllowedOperations.in_range.value,
        AllowedOperations.equality.value,
    ]

    @classmethod
    def validate_rule(cls, operation, value):
        super().validate_rule(operation, value)
        if operation == AllowedOperations.equality.value:
            ValueSpec.model_validate(value)
        elif operation == AllowedOperations.in_range.value:
            RangeSpec.model_validate(value)

    def get_value(self):
        start = self.context_object.date_of_birth or date(
            self.context_object.year_of_birth, 1, 1
        )
        end = (self.context_object.deceased_datetime or timezone.now()).date()
        return relativedelta(end, start).normalized()

    def convert_value_to_units(self, value, value_type):
        if value_type == "years":
            return value.years
        if value_type == "months":
            return value.years * 12 + value.months
        if value_type == "days":
            return value.years * 365 + value.months * 30 + value.days
        raise ValueError("Invalid value type")

    def evaluate_in_range(self, rule):
        value = self.get_value()
        value_type = rule.get("value_type", "years")

        age = self.convert_value_to_units(value, value_type or "years")
        return age >= int(rule["min"]) and age <= int(rule["max"])

    def evaluate_equality(self, rule):
        value = self.get_value()
        value_type = rule.get("value_type", "years")
        age = self.convert_value_to_units(value, value_type or "years")
        return age == int(rule["value"])


EvaluatorMetricsRegistry.register(PatientAgeMetric)
