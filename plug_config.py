from plugs.manager import PlugManager
from plugs.plug import Plug

plugs = [
    Plug(
        name="care_copilot",
        package_name="/app/care_copilot",
        version="",
        configs={},
    ),
]

manager = PlugManager(plugs)
