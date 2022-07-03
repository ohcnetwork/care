import enum

from rest_framework.exceptions import ValidationError

from care.utils.assetintegration.base import BaseAssetIntegration


class OnvifAsset(BaseAssetIntegration):
    _name = "onvif"

    class OnvifActions(enum.Enum):
        MOVE_ABSOLUTE = "move_absolute"
        GOTO_PRESET = "goto_preset"

    def __init__(self, meta):
        try:
            super().__init__(meta)
            self.name = self.meta["camera_type"]
            self.port = self.meta["camera_port"] or 80
            self.username = self.meta["camera_access_key"].split(":")[0]
            self.password = self.meta["access_credentials"].split(":")[1]
        except KeyError as e:
            raise ValidationError(
                dict((key, f"{key} not found in asset metadata") for key in e.args))

    def handle_action(self, action):
        if action["type"] == self.OnvifActions.MOVE_ABSOLUTE.value:
            # Make API Call for action
            request_data = {
                "x": action.data["x"],
                "y": action.data["y"],
                "z": action.data["z"],
                "speed": action.data["speed"],
                "meta": self.meta,
            }
            return self.api_post(self.get_url("absoluteMove"), data=request_data)

        elif action["type"] == self.OnvifActions.GOTO_PRESET.value:
            # Make API Call for action
            request_data = {
                "preset": action.preset,
                "meta": self.meta,
            }
            return self.api_post(self.get_url("gotoPreset"), data=request_data)
        elif action["type"] == self.OnvifActions.GOTO_PRESET.value:
            # Make API Call for action
            return self.api_get(self.get_url("status"), data={})
        else:
            raise ValidationError({"action": "invalid action type"})
