import enum

from care.utils.assetintegration.base import BaseAssetIntegration


class HL7MonitorAsset(BaseAssetIntegration):
    _name = "hl7monitor"

    class HL7MonitorActions(enum.Enum):
        GET_VITALS = "get_vitals"

    def __init__(self, meta):
        super().__init__(meta)

    def handle_action(self, action):
        if action["type"] == self.HL7MonitorActions.GET_VITALS.value:
            request_params = {
                "device_id": self.host
            }
            return self.api_get(self.get_url("vitals"), data=request_params)
        else:
            print("also here")
            raise Exception("Invalid action")

