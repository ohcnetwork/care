import enum

from rest_framework.exceptions import ValidationError

from care.utils.assetintegration.base import ActionParams, BaseAssetIntegration


class OnvifAsset(BaseAssetIntegration):
    _name = "onvif"

    class OnvifActions(enum.Enum):
        GET_CAMERA_STATUS = "get_status"
        GET_PRESETS = "get_presets"
        GOTO_PRESET = "goto_preset"
        ABSOLUTE_MOVE = "absolute_move"
        RELATIVE_MOVE = "relative_move"
        GET_STREAM_TOKEN = "get_stream_token"

    def __init__(self, meta):
        try:
            super().__init__(meta)
            self.username = self.meta["camera_access_key"].split(":")[0]
            self.password = self.meta["camera_access_key"].split(":")[1]
            self.access_key = self.meta["camera_access_key"].split(":")[2]
        except KeyError as e:
            raise ValidationError(
                {key: f"{key} not found in asset metadata" for key in e.args}
            ) from e

    def handle_action(self, **kwargs: ActionParams):
        action_type = kwargs["type"]
        action_data = kwargs.get("data", {})
        timeout = kwargs.get("timeout")

        request_body = {
            "hostname": self.host,
            "port": 80,
            "username": self.username,
            "password": self.password,
            "accessKey": self.access_key,
            **action_data,
        }

        if action_type == self.OnvifActions.GET_CAMERA_STATUS.value:
            return self.api_get(self.get_url("status"), request_body, timeout)

        if action_type == self.OnvifActions.GET_PRESETS.value:
            return self.api_get(self.get_url("presets"), request_body, timeout)

        if action_type == self.OnvifActions.GOTO_PRESET.value:
            return self.api_post(self.get_url("gotoPreset"), request_body, timeout)

        if action_type == self.OnvifActions.ABSOLUTE_MOVE.value:
            return self.api_post(self.get_url("absoluteMove"), request_body, timeout)

        if action_type == self.OnvifActions.RELATIVE_MOVE.value:
            return self.api_post(self.get_url("relativeMove"), request_body, timeout)

        if action_type == self.OnvifActions.GET_STREAM_TOKEN.value:
            return self.api_post(
                self.get_url("api/stream/getToken/videoFeed"),
                {
                    "stream_id": self.access_key,
                },
                timeout,
            )

        raise ValidationError({"action": "invalid action type"})
