import os

from plugs.manager import PlugManager
from plugs.plug import Plug

HCX_PROTOCOL_BASE_PATH = os.getenv(
    "HCX_PROTOCOL_BASE_PATH", default="http://staging-hcx.swasth.app/api/v0.7"
)
HCX_AUTH_BASE_PATH = os.getenv(
    "HCX_AUTH_BASE_PATH",
    default="https://staging-hcx.swasth.app/auth/realms/swasth-health-claim-exchange/protocol/openid-connect/token",
)
HCX_PARTICIPANT_CODE = os.getenv("HCX_PARTICIPANT_CODE", default="")
HCX_USERNAME = os.getenv("HCX_USERNAME", default="")
HCX_PASSWORD = os.getenv("HCX_PASSWORD", default="")
HCX_ENCRYPTION_PRIVATE_KEY_URL = os.getenv(
    "HCX_ENCRYPTION_PRIVATE_KEY_URL",
    default="https://raw.githubusercontent.com/Swasth-Digital-Health-Foundation/hcx-platform/main/hcx-apis/src/test/resources/examples/x509-private-key.pem",
)
HCX_IG_URL = os.getenv("HCX_IG_URL", default="https://ig.hcxprotocol.io/v0.7.1")
HCX_CERT_URL = os.getenv(
    "HCX_CERT_URL",
    default="https://raw.githubusercontent.com/Swasth-Digital-Health-Foundation/hcx-platform/main/hcx-apis/src/test/resources/examples/x509-self-signed-certificate.pem",
)
AUTH_USER_MODEL = "users.User"

hcx_plugin = Plug(
    name="hcx",
    package_name="git+https://github.com/ohcnetwork/care_hcx.git",
    version="@main",
    configs={
        "HCX_PROTOCOL_BASE_PATH": HCX_PROTOCOL_BASE_PATH,
        "HCX_AUTH_BASE_PATH": HCX_AUTH_BASE_PATH,
        "HCX_PARTICIPANT_CODE": HCX_PARTICIPANT_CODE,
        "HCX_USERNAME": HCX_USERNAME,
        "HCX_PASSWORD": HCX_PASSWORD,
        "HCX_ENCRYPTION_PRIVATE_KEY_URL": HCX_ENCRYPTION_PRIVATE_KEY_URL,
        "HCX_IG_URL": HCX_IG_URL,
        "HCX_CERT_URL": HCX_CERT_URL,
        "AUTH_USER_MODEL": AUTH_USER_MODEL,
    },
)

plugs = [hcx_plugin]

manager = PlugManager(plugs)
