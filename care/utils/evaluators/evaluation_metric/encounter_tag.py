from care.emr.models.tag_config import TagConfig
from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)


class EncounterTagsMetric(EvaluationMetricBase):
    context = "encounter"
    name = "encounter_tag"
    verbose_name = "Encounter Tag"
    allowed_operations = [
        AllowedOperations.has_tag.value,
    ]

    def clean_rule(self, rule):
        tag_ids = rule.split(",")
        tag_config = (
            TagConfig.objects.only("id")
            .filter(external_id__in=tag_ids)
            .values_list("id", flat=True)
        )
        if tag_config is None:
            return -1
        return tag_config

    def get_value(self, facility=None):
        encounter = self.context_object
        return [*encounter.tags]


EvaluatorMetricsRegistry.register(EncounterTagsMetric)
