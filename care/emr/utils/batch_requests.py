import logging

from django.db import transaction
from django.test.client import RequestFactory
from django.urls import Resolver404, resolve
from rest_framework.exceptions import ParseError

HEADERS_TO_INCLUDE = ["HTTP_USER_AGENT", "HTTP_AUTHORIZATION"]
DEFAULT_CONTENT_TYPE = "application/json"


def get_response(wsgi_request):
    try:
        with transaction.atomic():
            view, args, kwargs = resolve(wsgi_request.path_info)
            kwargs.update({"request": wsgi_request})
            resp = view(*args, **kwargs)
            data = resp.data
            headers = resp.headers.values()
            status_code = resp.status_code
    except Resolver404:
        data = {"detail": "Route not found"}
        headers = {}
        status_code = 404
    except Exception as exc:
        data = {"detail": "server_error"}
        headers = {}
        logging.exception(exc)
        status_code = 500
    return {"status_code": status_code, "headers": headers, "data": data}


def pre_process_method_headers(method, headers):
    method = method.lower()

    wsgi_headers = [
        "content_length",
        "content_type",
        "query_string",
        "remote_addr",
        "remote_host",
        "remote_user",
        "request_method",
        "server_name",
        "server_port",
    ]
    transformed_headers = {}

    for header, value in headers.items():
        new_header = header.replace("-", "_")
        http_header = (
            f"http_{new_header}"
            if new_header.lower() not in wsgi_headers
            else new_header
        )
        transformed_headers.update({http_header.upper(): value})
    return method, transformed_headers


def headers_to_include_from_request(curr_request):
    return {h: v for h, v in curr_request.META.items() if h in HEADERS_TO_INCLUDE}


def get_wsgi_request_object(curr_request, method, url, headers, body):
    x_headers = headers_to_include_from_request(curr_request)
    method, t_headers = pre_process_method_headers(method, headers)

    if "CONTENT_TYPE" not in t_headers:
        t_headers.update({"CONTENT_TYPE": DEFAULT_CONTENT_TYPE})

    x_headers.update(t_headers)
    content_type = x_headers.get("CONTENT_TYPE", DEFAULT_CONTENT_TYPE)

    request_factory = RequestFactory()
    request_provider = getattr(request_factory, method, None)

    if not request_provider:
        msg = f"Malformed request: {method} is not a valid HTTP method"
        raise ParseError(msg)

    secure = False

    return request_provider(
        url, data=body, secure=secure, content_type=content_type, **x_headers
    )


def execute_serially(requests, resp_generator):
    return [resp_generator(request) for request in requests]


def construct_wsgi_from_data(request, data):
    url = data.url
    body = data.body
    method = data.method
    headers = {}  # data.get("headers", {})
    return get_wsgi_request_object(request, method, url, headers, body)


def convert_batch_request_to_wsgi(parent_request, batch_request_data):
    return [
        construct_wsgi_from_data(parent_request, data)
        for data in batch_request_data.requests
    ]


def execute_batch_requests(parent_request, batch_request_data):
    wsgi_requests = convert_batch_request_to_wsgi(parent_request, batch_request_data)
    return execute_serially(wsgi_requests, get_response)
