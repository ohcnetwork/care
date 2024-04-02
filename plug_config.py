import environ

from plugs.manager import PlugManager
from plugs.plug import Plug

env = environ.Env()

scribe_plug = Plug(
    name="care_scribe",
    package_name="git+https://github.com/coronasafe/care_scribe.git",
    version="@scribe",
    configs={
        "TRANSCRIBE_SERVICE_PROVIDER_API_KEY": env(
            "TRANSCRIBE_SERVICE_PROVIDER_API_KEY"
        ),
    },
)

plugs = [scribe_plug]

manager = PlugManager(plugs)
