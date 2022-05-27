import json

from care.utils.assetintegration.base import BaseAssetIntegration


class HL7MonitorAsset(BaseAssetIntegration):
    _name = "hl7monitor"

    def __init__(self, meta):
        try:
            self.meta = json.loads(meta)
            self.meta = meta
            self.host = meta["local_ip_address"]
            self.username = meta["camera_access_key"].split(":")[0]
            self.password = meta["access_credentials"].split(":")[1]
        except KeyError:
            print("Error: Invalid HL7Monitor Asset; Missing required fields")

    def handle_action(self, action):
        pass
