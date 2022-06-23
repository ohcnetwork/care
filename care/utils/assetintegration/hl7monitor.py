from care.utils.assetintegration.base import BaseAssetIntegration


class HL7MonitorAsset(BaseAssetIntegration):
    _name = "hl7monitor"

    def __init__(self, meta):
        try:
            super().__init__(meta)
        except KeyError:
            print("Error: Invalid HL7Monitor Asset; Missing required fields")
