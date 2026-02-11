import logging

from django.db import transaction
from django.test.client import RequestFactory
from django.urls import Resolver404, resolve
from jsonpath_ng import parse
from rest_framework.exceptions import ParseError

logger = logging.getLogger(__name__)

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
        logger.exception(exc)
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


def find_and_replace_data(data, reference_id, replacements, data_references):
    for replacement in replacements:
        if replacement.value_path.reference_id == reference_id:
            source_reference_id = replacement.source_path.reference_id
            if source_reference_id in data_references:
                source = data_references[replacement.source_path.reference_id]
                source_query = parse(replacement.source_path.path)
                source_values = source_query.find(source)
                if not source_values:
                    error_msg = f"Invalid source_path '{replacement.source_path.path}' for request {reference_id}"
                    raise ParseError(error_msg)
                source_value = source_values[0].value
                destination_type = replacement.value_path.type
                if destination_type == "url":
                    value = "{" + replacement.value_path.path + "}"
                    if value not in data["url"]:
                        error_msg = f"URL path '{replacement.value_path.path}' not found in url for request {reference_id}"
                        raise ParseError(error_msg)
                    data["url"] = data["url"].replace(value, str(source_value))
                else:
                    destination_query = parse(replacement.value_path.path)
                    destination_values = destination_query.find(data["body"])
                    if not destination_values:
                        error_msg = f"Invalid destination_path '{replacement.value_path.path}' for request {reference_id}"
                        raise ParseError(error_msg)
                    for values in destination_values:
                        values.full_path.update(data["body"], source_value)


def execute_serially(
    parent_request, requests, resp_generator, replacements, data_references
):
    from care.emr.api.viewsets.batch_request import UnHandledError

    data_reference_required_id = {
        replacement.source_path.reference_id for replacement in replacements
    }
    responses = []
    for request in requests:
        find_and_replace_data(
            request, request["reference_id"], replacements, data_references
        )
        wsgi_request = get_wsgi_request_object(
            parent_request,
            request["method"],
            request["url"],
            request["headers"],
            request["body"],
        )
        response = resp_generator(wsgi_request)
        responses.append(response)
        if (
            request["reference_id"] in data_reference_required_id
            and response["status_code"] < 300  # noqa PLR2004
        ):
            data_references[request["reference_id"]] = response["data"]
        if response["status_code"] >= 500:  # noqa PLR2004
            raise UnHandledError
    return responses


def construct_wsgi_from_data(request, data):
    url = data.url
    body = data.body
    method = data.method
    headers = {}  # data.get("headers", {})
    return get_wsgi_request_object(request, method, url, headers, body)


def split_batch_request_data(batch_request_data):
    return [
        {
            "body": data.body,
            "reference_id": data.reference_id,
            "url": data.url,
            "method": data.method,
            "headers": {},
        }
        for data in batch_request_data.requests
    ]


def execute_batch_requests(
    parent_request, batch_request_data, replacements, data_references
):
    wsgi_requests = split_batch_request_data(batch_request_data)
    return execute_serially(
        parent_request, wsgi_requests, get_response, replacements, data_references
    )
