import enum

from rest_framework.exceptions import ValidationError

from care.utils.assetintegration.base import BaseAssetIntegration


class HL7MonitorAsset(BaseAssetIntegration):
    _name = "hl7monitor"

    class HL7MonitorActions(enum.Enum):
        GET_VITALS = "get_vitals"
        GET_CAMERA_STATUS = "get_status"
        GET_PRESETS = "get_presets"
        GOTO_PRESET = "goto_preset"
        ABSOLUTE_MOVE = "absolute_move"
        RELATIVE_MOVE = "relative_move"

    def __init__(self, meta):
        super().__init__(meta)
        self.port = self.meta["port"]
        self.username = self.meta["username"]
        self.password = self.meta["password"]

    def handle_action(self, action: dict[str, any]):
        action_type: str = action["type"]
        action_data: dict[str, any] = action.get("data", {})

        request_body = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            **action_data
        }

        if action_type == self.HL7MonitorActions.GET_VITALS.value:
            request_params = {"device_id": self.host}
            return self.api_get(self.get_url("vitals"), request_params)

        if action_type == self.HL7MonitorActions.GET_CAMERA_STATUS.value:
            return self.api_get(self.get_url("status"), request_body)

        if action_type == self.HL7MonitorActions.GET_PRESETS.value:
            return self.api_get(self.get_url("presets"), request_body)

        if action_type == self.HL7MonitorActions.GOTO_PRESET.value:
            return self.api_post(self.get_url("gotoPreset"), request_body)

        if action_type == self.HL7MonitorActions.ABSOLUTE_MOVE.value:
            return self.api_post(self.get_url("absoluteMove"), request_body)

        if action_type == self.HL7MonitorActions.RELATIVE_MOVE.value:
            return self.api_post(self.get_url("relativeMove"), request_body)

        raise ValidationError({"action": "invalid action type"})
