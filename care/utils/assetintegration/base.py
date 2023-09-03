import json
import logging

import requests
from django.conf import settings
from rest_framework.exceptions import APIException

from care.utils.jwks.token_generator import generate_jwt

logger = logging.getLogger(__name__)

MIDDLEWARE_REQUEST_TIMEOUT = 25


class BaseAssetIntegration:
    auth_header_type = "Care_Bearer "

    def __init__(self, meta):
        self.meta = meta
        self.host = self.meta["local_ip_address"]
        self.middleware_hostname = self.meta["middleware_hostname"]
        self.insecure_connection = self.meta.get("insecure_connection", False)

    def handle_action(self, action):
        pass

    def get_url(self, endpoint):
        protocol = "http"
        if not self.insecure_connection or settings.IS_PRODUCTION:
            protocol += "s"
        return f"{protocol}://{self.middleware_hostname}/{endpoint}"

    def api_post(self, url, data=None):
        try:
            response = requests.post(
                url,
                json=data,
                headers={"Authorization": (self.auth_header_type + generate_jwt())},
                timeout=MIDDLEWARE_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error("middleware error: %s", e.errno)
            raise APIException({"error": "error occurred on middleware"}) from None
        except json.decoder.JSONDecodeError:
            raise APIException({"error": "Invalid Response"}) from None

    def api_get(self, url, data=None):
        try:
            response = requests.get(
                url,
                params=data,
                headers={"Authorization": (self.auth_header_type + generate_jwt())},
                timeout=MIDDLEWARE_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error("middleware error: %s", e.errno)
            raise APIException({"error": "error occurred on middleware"}) from None
        except json.decoder.JSONDecodeError:
            raise APIException({"error": "Invalid Response"}) from None
