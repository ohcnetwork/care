import enum

from care.utils.assetintegration.hl7monitor import HL7MonitorAsset
from care.utils.assetintegration.onvif import OnvifAsset
from care.utils.assetintegration.ventilator import VentilatorAsset


class AssetClasses(enum.Enum):
    ONVIF = OnvifAsset
    HL7MONITOR = HL7MonitorAsset
    VENTILATOR = VentilatorAsset
