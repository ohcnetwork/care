import logging
import time
from datetime import datetime


class CustomFormatter(logging.Formatter):
    def format(self, record):
        return (
            f"INFO {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {record.getMessage()}"
        )


logger = logging.getLogger("time_logging_middleware")
logger.setLevel(logging.INFO)
logger.propagate = False

for handler in logger.handlers[:]:
    logger.removeHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())
logger.addHandler(handler)


class RequestTimeLoggingMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - request.start_time

        logger.info(f"Request to {request.path} took {duration:.4f} seconds")

        return response
