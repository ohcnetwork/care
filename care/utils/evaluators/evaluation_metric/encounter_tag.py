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
        tag_config = TagConfig.objects.only("id").filter(external_id=rule).first()
        if tag_config is None:
            return -1
        return tag_config.id

    def get_value(self):
        encounter = self.context_object
        facility_external_id = str(encounter.facility.external_id)
        patient = encounter.patient
        patient_facility_tags = patient.facility_tags.get(facility_external_id, [])
        patient_instance_tags = patient.instance_tags
        encounter_tags = encounter.tags
        return [*patient_facility_tags, *patient_instance_tags, *encounter_tags]


EvaluatorMetricsRegistry.register(EncounterTagsMetric)
