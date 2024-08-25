import logging
import time

from django.conf import settings


class RequestTimeLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("time_logging_middleware")

    def __call__(self, request):
        if not getattr(settings, "ENABLE_REQUEST_TIME_LOGGING", False):
            return self.get_response(request)

        request.start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - request.start_time
        self.logger.info(f"Request to {request.path} took {duration:.4f} seconds")
        return response
