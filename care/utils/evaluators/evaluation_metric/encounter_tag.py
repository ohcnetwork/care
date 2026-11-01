from datetime import datetime

from care.emr.models.tag_config import TagConfig
from care.utils.evaluators.evaluation_metric.base import EvaluationMetricBase
from care.utils.registries.evaluation_metric import (
    AllowedOperations,
    EvaluatorMetricsRegistry,
)
from care.utils.time_util import care_now


def active_tags(tags, tags_data):
    tags_data = tags_data or {}
    now = care_now()
    active = []
    for tag in tags or []:
        expiry = (tags_data.get(str(tag)) or {}).get("expiry")
        if expiry and now > datetime.fromisoformat(expiry):
            continue
        active.append(tag)
    return active


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
        if self._value_type == "encounter":
            return active_tags(encounter.tags, encounter.tags_data)
        patient = encounter.patient
        patient_facility_tags = patient.facility_tags.get(
            str(encounter.facility.id), []
        )
        patient_instance_tags = patient.instance_tags
        tags = [*patient_facility_tags, *patient_instance_tags]
        return active_tags(tags, patient.tags_data)


EvaluatorMetricsRegistry.register(EncounterTagsMetric)
