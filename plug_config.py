from plugs.manager import PlugManager
from plugs.plug import Plug

plugs = [
    Plug(
        name="care_encounter_auto_close_be",
        package_name="/Users/nandkishorr/work/care/care_encounter_auto_close_be",
        version="",
        configs={
            "CARE_ENCOUNTER_AUTO_CLOSE_ENABLED": True,
        },
    )
]


manager = PlugManager(plugs)
