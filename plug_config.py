import os

from plugs.manager import PlugManager
from plugs.plug import Plug

# ABDM
ENABLE_ABDM = os.getenv("ENABLE_ABDM")
ABDM_CLIENT_ID = os.getenv("ABDM_CLIENT_ID") or ""
ABDM_CLIENT_SECRET = os.getenv("ABDM_CLIENT_SECRET") or ""
ABDM_URL = os.getenv("ABDM_URL") or "https://dev.abdm.gov.in"
HEALTH_SERVICE_API_URL = (
    os.getenv("HEALTH_SERVICE_API_URL") or "https://healthidsbx.abdm.gov.in/api"
)
ABDM_FACILITY_URL = os.getenv("ABDM_FACILITY_URL") or "https://facilitysbx.abdm.gov.in"
HIP_NAME_PREFIX = os.getenv("HIP_NAME_PREFIX") or ""
HIP_NAME_SUFFIX = os.getenv("HIP_NAME_SUFFIX") or ""
ABDM_USERNAME = os.getenv("ABDM_USERNAME") or "abdm_user_internal"
X_CM_ID = os.getenv("X_CM_ID") or "sbx"
FIDELIUS_URL = os.getenv("FIDELIUS_URL") or "http://fidelius:8090"
AUTH_USER_MODEL = "users.User"


abdm_plugin = Plug(
    name="abdm",
    package_name="git+https://github.com/coronasafe/care_abdm.git",
    version="@main",
    configs={
        "ABDM_CLIENT_ID": ABDM_CLIENT_ID,
        "ABDM_CLIENT_SECRET": ABDM_CLIENT_SECRET,
        "ABDM_URL": ABDM_URL,
        "HEALTH_SERVICE_API_URL": HEALTH_SERVICE_API_URL,
        "ABDM_FACILITY_URL": ABDM_FACILITY_URL,
        "HIP_NAME_PREFIX": HIP_NAME_PREFIX,
        "HIP_NAME_SUFFIX": HIP_NAME_SUFFIX,
        "ABDM_USERNAME": ABDM_USERNAME,
        "X_CM_ID": X_CM_ID,
        "FIDELIUS_URL": FIDELIUS_URL,
        "AUTH_USER_MODEL": AUTH_USER_MODEL,
    },
)


plugs = [abdm_plugin]

manager = PlugManager(plugs)
