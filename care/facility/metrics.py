from django.db.models import Count
from prometheus_client.core import GaugeMetricFamily

from care.facility.models.facility import FACILITY_TYPES, Facility
from care.utils.metrics import metrics_registry


class FacilityCollector:
    def collect(self):
        categories = dict(FACILITY_TYPES)
        counts = dict.fromkeys(categories.values(), 0)
        counts["unknown"] = 0
        for row in (
            Facility.objects.values("facility_type")
            .annotate(count=Count("pk"))
            .order_by()
        ):
            category = categories.get(row["facility_type"], "unknown")
            counts[category] += row["count"]

        metric = GaugeMetricFamily(
            "care_facilities",
            "Current number of facilities by category, excluding deleted records.",
            labels=["category"],
        )
        for category, count in counts.items():
            metric.add_metric([category], count)
        yield metric


metrics_registry.register(FacilityCollector())
