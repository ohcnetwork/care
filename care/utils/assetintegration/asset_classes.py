import enum
from care.utils.assetintegration.onvif import OnvifAsset


class AssetClasses(enum.Enum):
    ONVIF = OnvifAsset
