import logging
import threading
import uuid
from hashlib import md5
from typing import NamedTuple

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse


class RequestInformation(NamedTuple):
    request_id: str
    request: HttpRequest
    response: HttpResponse | None
    exception: Exception | None


logger = logging.getLogger("audit_log")


class AuditLogMiddleware:
    thread = threading.local()

    def __init__(self, get_response):
        self.get_response = get_response
        AuditLogMiddleware.thread.__dal__ = None

    @staticmethod
    def is_request():
        return bool(getattr(AuditLogMiddleware.thread, "__dal__", None))

    @staticmethod
    def save(request, response=None, exception=None):
        """
        Helper middleware, that sadly needs to be present.
        the request_finished and request_started signals only
        expose the class, not the actual request and response.

        We save the request and response specific data in the thread.

        :param request: Django Request
        :param response: Optional Django Response
        :param exception: Optional Exception
        :return:
        """
        if not settings.AUDIT_LOG_ENABLED:
            return

        dal_request_id = getattr(request, "dal_request_id", None)
        if not dal_request_id:
            dal_request_id = (
                f"{request.method.lower()}::"
                f"{md5(request.path.lower().encode('utf-8')).hexdigest()}::"  # noqa: S324
                f"{uuid.uuid4().hex}"
            )
            request.dal_request_id = dal_request_id

        AuditLogMiddleware.thread.__dal__ = RequestInformation(
            dal_request_id, request, response, exception
        )

    @staticmethod
    def get_current_request_id():
        environ = RequestInformation(*AuditLogMiddleware.thread.__dal__)
        return environ.request_id

    @staticmethod
    def get_current_user():
        environ = RequestInformation(*AuditLogMiddleware.thread.__dal__)
        if isinstance(environ.request.user, AnonymousUser):
            return None
        return environ.request.user

    @staticmethod
    def get_current_request():
        environ = RequestInformation(*AuditLogMiddleware.thread.__dal__)
        return environ.request

    def __call__(self, request: HttpRequest):
        if request.method.lower() == "get":
            return self.get_response(request)

        self.save(request)
        response: HttpResponse = self.get_response(request)
        self.save(request, response)

        if getattr(request.user, "is_alternative_login", False):
            current_user_str = f"patient|{request.user.phone_number[-4:]}"
        else:
            current_user_str = (
                f"{request.user.id}|{request.user}" if request.user else None
            )

        logger.info(
            "%s %s %s User:[%s]",
            request.method,
            request.path,
            response.status_code,
            current_user_str,
        )
        return response

    def process_exception(self, request, exception):
        pass

    @staticmethod
    def cleanup():
        """
        Cleanup function, that should be called last. Overwrites the
        custom __dal__ object with None, to make sure the next request
        does not use the same object.

        :return: -
        """
        AuditLogMiddleware.thread.__dal__ = None
