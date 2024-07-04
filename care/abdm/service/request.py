import json
import logging

import requests
from django.conf import settings
from django.core.cache import cache

ABDM_GATEWAY_URL = settings.ABDM_URL + "/gateway"
ABDM_TOKEN_URL = ABDM_GATEWAY_URL + "/v0.5/sessions"
ABDM_TOKEN_CACHE_KEY = "abdm_token"

logger = logging.getLogger(__name__)


class Request:
    def __init__(self, base_url):
        self.url = base_url

    def user_header(self, user_token):
        if not user_token:
            return {}
        return {"X-Token": "Bearer " + user_token}

    def auth_header(self):
        token = cache.get(ABDM_TOKEN_CACHE_KEY)
        if not token:
            data = json.dumps(
                {
                    "clientId": settings.ABDM_CLIENT_ID,
                    "clientSecret": settings.ABDM_CLIENT_SECRET,
                }
            )
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            logger.info("No Token in Cache")
            response = requests.post(ABDM_TOKEN_URL, data=data, headers=headers)

            if response.status_code < 300:
                if response.headers["Content-Type"] != "application/json":
                    logger.info(
                        f"Unsupported Content-Type: {response.headers['Content-Type']}"
                    )
                    logger.info(f"Response: {response.text}")

                    return None
                else:
                    data = response.json()
                    token = data["accessToken"]
                    expires_in = data["expiresIn"]

                    logger.info(f"New Token: {token}")
                    logger.info(f"Expires in: {expires_in}")

                    cache.set(ABDM_TOKEN_CACHE_KEY, token, expires_in)
            else:
                logger.info(f"Bad Response: {response.text}")
                return None

        return {"Authorization": f"Bearer {token}"}

    def headers(self, additional_headers=None, auth=None):
        return {
            "Content-Type": "application/json",
            "Accept": "*/*",
            **(additional_headers or {}),
            **(self.user_header(auth) or {}),
            **(self.auth_header() or {}),
        }

    def get(self, path, params=None, headers=None, auth=None):
        url = self.url + path
        headers = self.headers(headers, auth)

        logger.info(f"GET: {url}")
        response = requests.get(url, headers=headers, params=params)
        logger.info(f"{response.status_code} Response: {response.text}")

        return self._handle_response(response)

    def post(self, path, data=None, headers=None, auth=None):
        url = self.url + path
        payload = json.dumps(data)
        headers = self.headers(headers, auth)

        logger.info(f"POST: {url}, {headers}, {data}")
        response = requests.post(url, data=payload, headers=headers)
        logger.info(f"{response.status_code} Response: {response.text}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response):
        def custom_json():
            try:
                return response.json()
            except ValueError as json_err:
                logger.error(f"JSON Decode error: {json_err}")
                return {"error": response.text}
            except Exception as err:
                logger.error(f"Unknown error while decoding json: {err}")
                return {}

        response.json = custom_json
        return response
