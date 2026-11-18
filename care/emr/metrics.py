from django.db.models import Count
from prometheus_client.core import GaugeMetricFamily

from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.resources.encounter.constants import ClassChoices
from care.utils.metrics import metrics_registry


class PatientCollector:
    def collect(self):
        yield GaugeMetricFamily(
            "care_patients_registered",
            "Current number of registered patients, excluding deleted records.",
            value=Patient.objects.count(),
        )


class EncounterCollector:
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

        yield GaugeMetricFamily(
            "care_encounters",
            "Current number of encounters across all statuses, excluding deleted records.",
            value=sum(counts.values()),
        )
        by_type = GaugeMetricFamily(
            "care_encounters_by_type",
            "Current number of encounters by encounter class, excluding deleted records.",
            labels=["type"],
        )
        for encounter_type, count in counts.items():
            by_type.add_metric([encounter_type], count)
        yield by_type


metrics_registry.register(PatientCollector())
metrics_registry.register(EncounterCollector())
