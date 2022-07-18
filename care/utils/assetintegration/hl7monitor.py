import enum

from rest_framework.exceptions import ValidationError

from care.utils.assetintegration.base import BaseAssetIntegration


class HL7MonitorAsset(BaseAssetIntegration):
    _name = "hl7monitor"

    class HL7MonitorActions(enum.Enum):
        GET_VITALS = "get_vitals"

    def __init__(self, meta):
        try:
            super().__init__(meta)
        except KeyError as e:
            raise ValidationError(
                dict((key, f"{key} not found in asset metadata") for key in e.args))

    def handle_action(self, action):
        action_type = action["type"]

        if action_type == self.HL7MonitorActions.GET_VITALS.value:
            request_params = {"device_id": self.host}
            return self.api_get(self.get_url("vitals"), request_params)

        raise ValidationError({"action": "invalid action type"})
