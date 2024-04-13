import subprocess
import sys
from collections import defaultdict


class PlugManager:
    """
    Manager to manage plugs in care
    """

    def __init__(self, plugs):
        self.plugs = plugs

    def install(self):
        packages = [x.package_name + x.version for x in self.plugs]
        if packages:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", " ".join(packages)]
            )

    def get_apps(self):
        return [plug.name for plug in self.plugs]

    def get_config(self):
        configs = defaultdict(dict)
        for plug in self.plugs:
            for key, value in plug.configs.items():
                configs[plug.name][key] = value
        return configs
