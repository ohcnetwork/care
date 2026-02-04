from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)


class EncounterClassMetric(EvaluationMetricBase):
    context = "encounter"
    name = "encounter_class"
    verbose_name = "Encounter Class"
    allowed_operations = [
        AllowedOperations.equality.value,
    ]

    def get_value(self):
        return self.context_object.encounter_class


EvaluatorMetricsRegistry.register(EncounterClassMetric)
