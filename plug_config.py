from plugs.manager import PlugManager
from plugs.plug import Plug

care_scribe = Plug(
    name="care_scribe",
    package_name="git+https://github.com/eka-care/care_scribe.git",
    version="@main",
)

plugs = [care_scribe]

manager = PlugManager(plugs)
