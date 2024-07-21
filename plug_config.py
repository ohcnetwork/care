from django.conf import settings

from plugs.manager import PlugManager
from plugs.plug import Plug

abdm_plugin = Plug(
    name="care_abdm",
    package_name="git+https://github.com/coronasafe/care_abdm.git",
    version="@v1.0.0",
    configs={
        "ABDM_CLIENT_ID": settings.ABDM_CLIENT_ID,
        "ABDM_CLIENT_SECRET": settings.ABDM_CLIENT_SECRET,
        "ABDM_URL": settings.ABDM_URL,
        "HEALTH_SERVICE_API_URL": settings.HEALTH_SERVICE_API_URL,
        "ABDM_FACILITY_URL": settings.ABDM_FACILITY_URL,
        "HIP_NAME_PREFIX": settings.HIP_NAME_PREFIX,
        "HIP_NAME_SUFFIX": settings.HIP_NAME_SUFFIX,
        "ABDM_USERNAME": settings.ABDM_USERNAME,
        "X_CM_ID": settings.X_CM_ID,
        "FIDELIUS_URL": settings.FIDELIUS_URL,
    },
)

plugs = [abdm_plugin]

manager = PlugManager(plugs)
