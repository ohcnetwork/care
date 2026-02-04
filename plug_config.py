from plugs.manager import PlugManager
from plugs.plug import Plug


plugs = [
    Plug(
        name="care_radiology",
        package_name="git+https://github.com/10bedicu/care_radiology.git",
        version="@main",
        configs={},
    )
]

manager = PlugManager(plugs)
