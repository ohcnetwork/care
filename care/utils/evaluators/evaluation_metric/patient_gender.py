from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)


class PatientGenderMetric(EvaluationMetricBase):
    context = "patient"
    name = "patient_gender"
    verbose_name = "Patient Gender"
    allowed_operations = [
        AllowedOperations.equality.value,
    ]

    def get_value(self):
        return self.context_object.gender


EvaluatorMetricsRegistry.register(PatientGenderMetric)
