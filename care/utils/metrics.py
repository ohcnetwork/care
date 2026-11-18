from django.conf import settings
from django.core.cache import cache
from prometheus_client import CollectorRegistry, generate_latest

metrics_registry = CollectorRegistry(auto_describe=False)


def get_metrics_payload():
    timeout = settings.PROMETHEUS_METRICS_CACHE_TTL
    if timeout <= 0:
        return generate_latest(metrics_registry)

    return cache.get_or_set(
        "prometheus:metrics:v1",
        lambda: generate_latest(metrics_registry),
        timeout=timeout,
    )
