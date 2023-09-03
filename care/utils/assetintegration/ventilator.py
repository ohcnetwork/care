import enum

from rest_framework.exceptions import ValidationError

from care.utils.assetintegration.base import BaseAssetIntegration


class VentilatorAsset(BaseAssetIntegration):
    _name = "ventilator"

    class VentilatorActions(enum.Enum):
        GET_VITALS = "get_vitals"

    def __init__(self, meta):
        try:
            super().__init__(meta)
        except KeyError as e:
            raise ValidationError(
                dict((key, f"{key} not found in asset metadata") for key in e.args),
            ) from None

    def handle_action(self, action):
        action_type = action["type"]

        if action_type == self.VentilatorActions.GET_VITALS.value:
            request_params = {"device_id": self.host}
            return self.api_get(self.get_url("vitals"), request_params)

        raise ValidationError({"action": "invalid action type"})
