from django.db.models import Count
from prometheus_client.core import GaugeMetricFamily

from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.resources.encounter.constants import ClassChoices
from care.utils.metrics import metrics_registry


class PatientCollector:
    def describe(self):
        yield GaugeMetricFamily(
            "care_patients_registered",
            "Current number of registered patients, excluding deleted records.",
        )

    def collect(self):
        metric = next(self.describe())
        metric.add_metric([], Patient.objects.count())
        yield metric


class EncounterCollector:
    def describe(self):
        yield GaugeMetricFamily(
            "care_encounters",
            "Current number of encounters across all statuses, excluding deleted records.",
        )
        yield GaugeMetricFamily(
            "care_encounters_by_type",
            "Current number of encounters by encounter class, excluding deleted records.",
            labels=["type"],
        )

    def collect(self):
        counts = {encounter_type.value: 0 for encounter_type in ClassChoices}
        counts["unknown"] = 0
        for row in (
            Encounter.objects.values("encounter_class")
            .annotate(count=Count("pk"))
            .order_by()
        ):
            encounter_type = row["encounter_class"]
            if encounter_type not in counts:
                encounter_type = "unknown"
            counts[encounter_type] += row["count"]

        total, by_type = self.describe()
        total.add_metric([], sum(counts.values()))
        yield total
        for encounter_type, count in counts.items():
            by_type.add_metric([encounter_type], count)
        yield by_type


metrics_registry.register(PatientCollector())
metrics_registry.register(EncounterCollector())
