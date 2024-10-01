import json

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException

from care.utils.jwks.token_generator import generate_jwt


class BaseAssetIntegration:
    auth_header_type = "Care_Bearer "

    def __init__(self, meta):
        self.meta = meta
        self.id = self.meta.get("id", "")
        self.host = self.meta["local_ip_address"]
        self.middleware_hostname = self.meta["middleware_hostname"]
        self.insecure_connection = self.meta.get("insecure_connection", False)
        self.timeout = settings.MIDDLEWARE_REQUEST_TIMEOUT

    def handle_action(self, action):
        pass

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

    def _validate_response(self, response: requests.Response):
        try:
            if response.status_code >= status.HTTP_400_BAD_REQUEST:
                raise APIException(response.text, response.status_code)
            return response.json()

        except requests.Timeout as e:
            raise APIException({"error": "Request Timeout"}, 504) from e

        except json.decoder.JSONDecodeError as e:
            raise APIException(
                {"error": "Invalid Response"}, response.status_code
            ) from e

    def api_post(self, url, data=None):
        return self._validate_response(
            requests.post(
                url, json=data, headers=self.get_headers(), timeout=self.timeout
            )
        )

    def api_get(self, url, data=None):
        return self._validate_response(
            requests.get(
                url, params=data, headers=self.get_headers(), timeout=self.timeout
            )
        )
