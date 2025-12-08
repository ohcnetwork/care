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

    def evaluate_has_tag(self, rule):
        self._value_type = rule.get("value_type", "encounter")
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
        encounter = self.context_object
        facility_external_id = str(encounter.facility.external_id)
        if self._value_type == "encounter":
            return [*encounter.tags]
        patient = encounter.patient
        patient_facility_tags = patient.facility_tags.get(facility_external_id, [])
        patient_instance_tags = patient.instance_tags
        return [*patient_facility_tags, *patient_instance_tags]


EvaluatorMetricsRegistry.register(EncounterTagsMetric)
