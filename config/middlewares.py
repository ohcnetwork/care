import logging
import time


class RequestTimeLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("time_logging_middleware")

    def __call__(self, request):
        request.start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - request.start_time
        self.logger.info("Request to %s took %.4f seconds", request.path, duration)
        return response
