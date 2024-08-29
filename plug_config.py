import os

from plugs.manager import PlugManager
from plugs.plug import Plug

abdm_plugin = Plug(
    name="abdm",
    package_name="git+https://github.com/ohcnetwork/care_abdm.git",
    version="@main",
    configs={},
)

plugs = [abdm_plugin]

manager = PlugManager(plugs)
