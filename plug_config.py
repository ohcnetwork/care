from plugs.manager import PlugManager
from plugs.plug import Plug

hcx_plugin = Plug(
    name="hcx",
    package_name="git+https://github.com/ohcnetwork/care_hcx.git",
    version="@sainak/fix-compatibility-with-care",
    configs={},
)

plugs = [hcx_plugin]

manager = PlugManager(plugs)
