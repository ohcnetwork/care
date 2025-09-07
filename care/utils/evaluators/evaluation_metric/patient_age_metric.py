from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)


class PatientAgeMetric(EvaluationMetricBase):
    context = "patient"
    name = "patient_age"
    allowed_operations = [
        AllowedOperations.in_range.value,
        AllowedOperations.equality.value,
    ]

    def get_value(self):
        return self.context_object.age


EvaluatorMetricsRegistry.register(PatientAgeMetric)
