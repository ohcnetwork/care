from plugs.manager import PlugManager
from plugs.plug import Plug

abdm_plugin = Plug(
    name="abdm",
    package_name="git+https://github.com/ohcnetwork/care_abdm.git",
    version="@main",
    configs={},
)

hcx_plugin = Plug(
    name="hcx",
    package_name="git+https://github.com/ohcnetwork/care_hcx.git",
    version="@main",
    configs={},
)

plugs = [hcx_plugin, abdm_plugin]

manager = PlugManager(plugs)
