import enum
import json
from urllib import request

from care.utils.assetintegration.base import BaseAssetIntegration


class OnvifAsset(BaseAssetIntegration):
    _name = "onvif"

    class OnvifActions(enum.Enum):
        MOVE_ABSOLUTE = "move_absolute"
        GOTO_PRESET = "goto_preset"

    def __init__(self, meta):
        try:
            self.meta = json.loads(meta)
            self.meta = meta
            self.name = meta["camera_type"]
            self.host = meta["local_ip_address"]
            self.port = meta["camera_port"] or 80
            self.username = meta["camera_access_key"].split(":")[0]
            self.password = meta["access_credentials"].split(":")[1]
            self.middleware_hostname = meta["middleware_hostname"]
        except KeyError:
            print("Error: Invalid Onvif Asset; Missing required fields")

    def get_url(self, endpoint):
        return "http://{}{}".format(self.middleware_hostname, endpoint)

    def api_post(self, url, data=None):
        req = request.post(url, json=data)
        try:
            return req.json()
        except json.decoder.JSONDecodeError:
            return {"error": "Invalid Response"}

    def api_get(self, url, data=None):
        req = request.get(url, data=data)
        try:
            return req.json()
        except json.decoder.JSONDecodeError:
            return {"error": "Invalid Response"}

    def handle_action(self, action):
        if action.type == self.OnvifActions.MOVE_ABSOLUTE.value:
            # Make API Call for action
            request_data = {
                "x": action.data["x"],
                "y": action.data["y"],
                "z": action.data["z"],
                "speed": action.data["speed"],
                "meta": self.meta,
            }
            return self.api_post(self.get_url("absoluteMove"), data=request_data)

        elif action.type == self.OnvifActions.GOTO_PRESET.value:
            # Make API Call for action
            request_data = {
                "preset": action.preset,
                "meta": self.meta,
            }
            return self.api_post(self.get_url("gotoPreset"), data=request_data)
        elif action.type == self.OnvifActions.GOTO_PRESET.value:
            # Make API Call for action
            return self.api_get(self.get_url("status"), data={})
        else:
            raise Exception("Invalid action")
