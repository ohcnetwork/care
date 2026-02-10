from plugs.manager import PlugManager
from plugs.plug import Plug

plugs = [
    Plug(
        name="care_radiology",
        package_name="git+https://github.com/10bedicu/care_radiology.git",
        version="@main",
        configs={},
    ),
    Plug(
        name="care_state_hmis",
        package_name="git+https://github.com/10bedicu/care_state_hmis.git",
        version="@restructure",
        configs={},
    ),
    Plug(
        name="abdm",
        package_name="git+https://github.com/10bedicu/care_abdm.git",
        version="@develop",
        configs={},
    ),
    Plug(
        name="care_scribe",
        package_name="git+https://github.com/10bedicu/care_scribe.git",
        version="@master",
        configs={},
    ),
]

manager = PlugManager(plugs)
