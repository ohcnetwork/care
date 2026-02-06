from plugs.manager import PlugManager
from plugs.plug import Plug  # noqa: F401

plugs = [
    Plug(
        name="care_state_hmis",
        package_name="git+https://github.com/10bedicu/care_state_hmis.git",
        version="@main",
        configs={},
    ),
    Plug(
        name="abdm",
        package_name="git+https://github.com/10bedicu/care_abdm.git",
        version="@develop",
        configs={},
    )
]

manager = PlugManager(plugs)
