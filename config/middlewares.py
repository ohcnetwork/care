import logging
import time

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "care_requests_total", "Total number of requests", ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "care_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

REQUESTS_IN_PROGRESS = Gauge(
    "care_requests_in_progress",
    "Number of requests currently being processed",
    ["method", "endpoint"],
)


class RequestTimeLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("time_logging_middleware")

    def __call__(self, request):
        # Start timing the request
        request.start_time = time.time()

        # Increment in-progress requests
        REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=request.path).inc()

        try:
            # Process the request
            response = self.get_response(request)

            # Record request duration
            duration = time.time() - request.start_time
            REQUEST_LATENCY.labels(
                method=request.method, endpoint=request.path
            ).observe(duration)

            # Increment request count
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.path,
                status=response.status_code,
            ).inc()

            # Log the request duration
            self.logger.info("Request to %s took %.4f seconds", request.path, duration)

            return response

        finally:
            # Decrement in-progress requests
            REQUESTS_IN_PROGRESS.labels(
                method=request.method, endpoint=request.path
            ).dec()


class PrometheusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip metrics endpoint to avoid infinite recursion
        if request.path == "/metrics":
            return self.get_response(request)

        # Get endpoint name (remove query parameters and trailing slashes)
        endpoint = request.path.rstrip("/")
        if not endpoint:
            endpoint = "/"

        # Increment in-progress requests
        REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=endpoint).inc()

        # Start timer
        start_time = time.time()

        # Process request
        response = self.get_response(request)

        # Record metrics
        duration = time.time() - start_time
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(
            duration
        )
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        # Decrement in-progress requests
        REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=endpoint).dec()

        return response
