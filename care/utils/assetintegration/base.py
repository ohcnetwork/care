import json
from typing import TypedDict

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException

from care.utils.jwks.token_generator import generate_jwt


class ActionParams(TypedDict, total=False):
    type: str
    data: dict | None
    timeout: int | None


class BaseAssetIntegration:
    auth_header_type = "Care_Bearer "

    def __init__(self, meta):
        self.meta = meta
        self.id = self.meta.get("id", "")
        self.host = self.meta["local_ip_address"]
        self.middleware_hostname = self.meta["middleware_hostname"]
        self.insecure_connection = self.meta.get("insecure_connection", False)
        self.timeout = settings.MIDDLEWARE_REQUEST_TIMEOUT

    def handle_action(self, **kwargs):
        """Handle actions using kwargs instead of dict."""

    def get_url(self, endpoint):
        protocol = "http"
        if not self.insecure_connection or settings.IS_PRODUCTION:
            protocol += "s"
        return f"{protocol}://{self.middleware_hostname}/{endpoint}"

    def get_headers(self):
        return {
            "Authorization": (self.auth_header_type + generate_jwt()),
            "Accept": "application/json",
        }

    def api_post(self, url, data=None, timeout=None):
        if timeout is None:
            timeout = self.timeout
        req = requests.post(
            url,
            json=data,
            headers=self.get_headers(),
            timeout=timeout,
        )
        try:
            response = req.json()
            if req.raise_for_status():
                raise APIException(response, req.status_code)
            return response

        except requests.Timeout:
            raise APIException(
                {"error": "Request Timeout"}, status.HTTP_504_GATEWAY_TIMEOUT
            )

        except json.decoder.JSONDecodeError:
            raise APIException({"error": "Invalid Response"}, req.status_code)

    def api_get(self, url, data=None, timeout=None):
        if timeout is None:
            timeout = self.timeout
        req = requests.get(
            url,
            params=data,
            headers=self.get_headers(),
            timeout=timeout,
        )
        try:
            if req.raise_for_status():
                raise APIException(req.text, req.status_code)
            return req.json()

        except requests.Timeout:
            raise APIException(
                {"error": "Request Timeout"}, status.HTTP_504_GATEWAY_TIMEOUT
            )

        except json.decoder.JSONDecodeError:
            raise APIException({"error": "Invalid Response"}, req.status_code)
