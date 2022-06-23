import json
import requests


class BaseAssetIntegration:
    def __init__(self, meta):
        self.meta = json.loads(meta)
        self.host = self.meta["local_ip_address"]
        self.middleware_hostname = self.meta["middleware_hostname"]

    def handle_action(self, action):
        pass

    def get_url(self, endpoint):
        return "http://{}{}".format(self.middleware_hostname, endpoint)


    def api_post(self, url, data=None):
        req = requests.post(url, json=data)
        try:
            return req.json()
        except json.decoder.JSONDecodeError:
            return {"error": "Invalid Response"}

    def api_get(self, url, data=None):
        req = requests.get(url, params=data)
        try:
            return req.json()
        except json.decoder.JSONDecodeError:
            return {"error": "Invalid Response"}
