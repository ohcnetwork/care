from dataclasses import dataclass


@dataclass
class Plug:
    name: str
    package_name: str
    version: str
    configs: dict
