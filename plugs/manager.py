import json
import logging
import os
import subprocess
import sys
from collections import defaultdict

from plugs.plug import Plug

logger = logging.getLogger(__name__)


class PlugManager:
    """
    Manager to manage plugs in care
    """

    def __init__(self, plugs: list[Plug]):
        self.plugs: list[Plug] = plugs

        # load additional plugs from environment variable
        if additional_plugs := os.getenv("ADDITIONAL_PLUGS"):
            try:
                for plug in json.loads(additional_plugs):
                    self.add_plug(Plug(**plug))
            except json.JSONDecodeError:
                logger.error("ADDITIONAL_PLUGS is not a valid JSON")

    def install(self) -> None:
        packages = {f"{x.package_name}{x.version}" for x in self.plugs}
        if packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])  # noqa: S603

    def add_plug(self, plug: Plug) -> None:
        if not isinstance(plug, Plug):
            msg = "plug must be an instance of Plug"
            raise ValueError(msg)
        self.plugs.append(plug)

    def get_apps(self) -> list[str]:
        return [plug.name for plug in self.plugs]

    def get_config(self) -> defaultdict[str, dict]:
        configs: defaultdict[str, dict] = defaultdict(dict)
        for plug in self.plugs:
            if plug.configs is None:
                continue
            for key, value in plug.configs.items():
                configs[plug.name][key] = value
        return configs
