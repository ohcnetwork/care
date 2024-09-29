from plugs.manager import PlugManager
from plugs.plug import Plug

hcx_plugin = Plug(
    name="hcx",
    package_name="git+https://github.com/ohcnetwork/care_hcx.git",
    version="@main",
    configs={},
)

livekit_plugin = Plug(
    name="livekit",
    package_name="git+https://github.com/ohcnetwork/care_livekit.git",
    version="@main",
    configs={},
)

plugs = [hcx_plugin, livekit_plugin]

manager = PlugManager(plugs)
