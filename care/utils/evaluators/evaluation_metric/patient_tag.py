from care.emr.models.tag_config import TagConfig
from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)


class PatientTagsMetric(EvaluationMetricBase):
    context = "patient"
    name = "patient_tag"
    verbose_name = "Patient Tag"
    allowed_operations = [
        AllowedOperations.has_tag.value,
    ]

    def evaluate_has_tag(self, rule):
        value = self.get_value()
        rule = self.clean_rule(rule)
        return any(tag in value for tag in rule)

    def clean_rule(self, rule):
        tag_ids = rule.get("value", "").split(",")
        tag_config = (
            TagConfig.objects.only("id")
            .filter(external_id__in=tag_ids)
            .values_list("id", flat=True)
        )
        if tag_config is None:
            return -1
        return tag_config

    def get_value(self):
        patient = self.context_object
        facility = self.context.get("facility")
        if not facility:
            return []
        patient_facility_tags = patient.facility_tags.get(str(facility.external_id), [])
        patient_instance_tags = patient.instance_tags
        return [*patient_facility_tags, *patient_instance_tags]


EvaluatorMetricsRegistry.register(PatientTagsMetric)
