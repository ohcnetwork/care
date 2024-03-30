from plugs.manager import PlugManager
from plugs.plug import Plug

scribe_plug = Plug(
    name="care_scribe",
    package_name="git+https://github.com/coronasafe/care_scribe.git",
    version="@master",
    configs={},
)

plugs = [scribe_plug]

manager = PlugManager(plugs)
