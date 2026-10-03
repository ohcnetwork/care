import json
import logging
import os
import subprocess
import sys
from collections import defaultdict
from importlib.metadata import distributions

from plugs.plug import Plug

logger = logging.getLogger(__name__)


class PlugManager:
    """
    Manager to manage plugs in care
    """

    def __init__(self, plugs: list[Plug]):
        self.plugs: dict[str, Plug] = {plug.name: plug for plug in plugs}

        # load additional plugs from environment variable
        if additional_plugs := os.getenv("ADDITIONAL_PLUGS"):
            try:
                for plug in json.loads(additional_plugs):
                    self.add_plug(Plug(**plug))
            except json.JSONDecodeError:
                logger.error("ADDITIONAL_PLUGS is not a valid JSON")

    def install(self) -> None:
        packages = set()
        for plug in self.plugs.values():
            if plug.package_name:
                packages.add(f"{plug.package_name}{plug.version}")
        if packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])  # noqa: S603

    def autodetect_installed_plugs(self) -> list[str]:
        # autodetect installed plugs starting with 'care_'
        # these plugins will be using environment variables for configs
        installed_plugins = []
        for dist in distributions():
            if (
                dist.name.startswith("care_")
                and dist.requires
                and any("django" in req.lower() for req in dist.requires)
            ):
                installed_plugins.append(dist.name)
        return installed_plugins

    def add_plug(self, plug: Plug) -> None:
        if not isinstance(plug, Plug):
            msg = "plug must be an instance of Plug"
            raise ValueError(msg)
        self.plugs[plug.name] = plug

    def get_apps(self) -> list[str]:
        installed_plugs = set(self.autodetect_installed_plugs())
        for plug in self.plugs.values():
            installed_plugs.add(plug.name)
        return list(installed_plugs)

    def get_config(self) -> defaultdict[str, dict]:
        configs: defaultdict[str, dict] = defaultdict(dict)
        for plug in self.plugs.values():
            if plug.configs is None:
                continue
            for key, value in plug.configs.items():
                configs[plug.name][key] = value
        return configs
