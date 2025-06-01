import logging
import os
import time

from django.conf import settings
from prometheus_client import Counter, Gauge, Histogram

ENVIRONMENT = getattr(settings, "CARE_ENVIRONMENT", None) or os.environ.get(
    "CARE_ENVIRONMENT", "local"
)

REQUEST_COUNT = Counter(
    "care_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status", "environment"],
)

REQUEST_LATENCY = Histogram(
    "care_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint", "environment"],
)

REQUESTS_IN_PROGRESS = Gauge(
    "care_requests_in_progress",
    "Number of requests currently being processed",
    ["method", "endpoint", "environment"],
)


class RequestTimeLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("time_logging_middleware")

    def __call__(self, request):
        request.start_time = time.time()

        REQUESTS_IN_PROGRESS.labels(
            method=request.method, endpoint=request.path, environment=ENVIRONMENT
        ).inc()

        try:
            response = self.get_response(request)

            duration = time.time() - request.start_time
            REQUEST_LATENCY.labels(
                method=request.method, endpoint=request.path, environment=ENVIRONMENT
            ).observe(duration)

            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.path,
                status=response.status_code,
                environment=ENVIRONMENT,
            ).inc()

            self.logger.info("Request to %s took %.4f seconds", request.path, duration)
            return response

        finally:
            REQUESTS_IN_PROGRESS.labels(
                method=request.method, endpoint=request.path, environment=ENVIRONMENT
            ).dec()


class PrometheusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip metrics endpoint to avoid infinite recursion
        if request.path == "/metrics":
            return self.get_response(request)

        endpoint = request.path.rstrip("/") or "/"

        REQUESTS_IN_PROGRESS.labels(
            method=request.method, endpoint=endpoint, environment=ENVIRONMENT
        ).inc()

        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time
        REQUEST_LATENCY.labels(
            method=request.method, endpoint=endpoint, environment=ENVIRONMENT
        ).observe(duration)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
            environment=ENVIRONMENT,
        ).inc()

        REQUESTS_IN_PROGRESS.labels(
            method=request.method, endpoint=endpoint, environment=ENVIRONMENT
        ).dec()

        return response
