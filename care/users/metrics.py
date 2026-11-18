from prometheus_client.core import GaugeMetricFamily

from care.users.models import User
from care.utils.metrics import metrics_registry


class UserCollector:
    def collect(self):
        yield GaugeMetricFamily(
            "care_users",
            "Current number of users, excluding deleted records.",
            value=User.objects.count(),
        )


metrics_registry.register(UserCollector())
