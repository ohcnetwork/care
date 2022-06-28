import json

import requests
from rest_framework.exceptions import APIException


class BaseAssetIntegration:
    def __init__(self, meta):
        self.meta = meta
        self.host = self.meta["local_ip_address"]
        self.middleware_hostname = self.meta["middleware_hostname"]

    def handle_action(self, action):
        pass

    def get_url(self, endpoint):
        return "http://{}/{}".format(self.middleware_hostname, endpoint)

    def api_post(self, url, data=None):
        req = requests.post(url, json=data)
        try:
            response = req.json()
            if req.status_code >= 400:
                raise APIException(response, req.status_code)
            return response
        except json.decoder.JSONDecodeError as e:
            return {"error": "Invalid Response"}

    def api_get(self, url, data=None):
        req = requests.get(url, params=data)
        try:
            response = req.json()
            if req.status_code >= 400:
                raise APIException(response, req.status_code)
            return response
        except json.decoder.JSONDecodeError as e:
            return {"error": "Invalid Response"}
