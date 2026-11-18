from prometheus_client.core import GaugeMetricFamily

from care.users.models import User
from care.utils.metrics import metrics_registry


class UserCollector:
    def describe(self):
        yield GaugeMetricFamily(
            "care_users",
            "Current number of users, excluding deleted records.",
        )

    def collect(self):
        metric = next(self.describe())
        metric.add_metric([], User.objects.count())
        yield metric


metrics_registry.register(UserCollector())
