import enum

from rest_framework.exceptions import ValidationError

from care.utils.assetintegration.base import BaseAssetIntegration


class VentilatorAsset(BaseAssetIntegration):
    _name = "ventilator"

    class VentilatorActions(enum.Enum):
        GET_VITALS = "get_vitals"
        GET_STREAM_TOKEN = "get_stream_token"

    def __init__(self, meta):
        try:
            super().__init__(meta)
        except KeyError as e:
            raise ValidationError(
                dict((key, f"{key} not found in asset metadata") for key in e.args)
            )

    def handle_action(self, action):
        action_type = action["type"]

        if action_type == self.VentilatorActions.GET_VITALS.value:
            request_params = {"device_id": self.host}
            return self.api_get(self.get_url("vitals"), request_params)

        if action_type == self.VentilatorActions.GET_STREAM_TOKEN.value:
            return self.api_post(
                self.get_url("api/stream/getToken/vitals"),
                {
                    "asset_id": self.id,
                    "ip": self.host,
                },
            )

        raise ValidationError({"action": "invalid action type"})
