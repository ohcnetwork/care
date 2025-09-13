from datetime import date

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)


class PatientAgeMetric(EvaluationMetricBase):
    context = "patient"
    name = "patient_age"
    verbose_name = "Patient Age"
    allowed_operations = [
        AllowedOperations.in_range.value,
        AllowedOperations.equality.value,
    ]

    def get_value(self):
        start = self.context_object.date_of_birth or date(self.context_object.year_of_birth, 1, 1)
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

    def evaluate_equality(self, rule, value_type):
        value = self.get_value()
        age = self.convert_value_to_units(value, value_type or "years")
        return age == int(rule)

    def evaluate_in_range(self, rule, value_type):
        value = self.get_value()
        min_value = int(rule["min"])
        max_value = int(rule["max"])
        age = self.convert_value_to_units(value, value_type or "years")
        return age >= min_value and age <= max_value

EvaluatorMetricsRegistry.register(PatientAgeMetric)
