from dataclasses import _MISSING_TYPE, dataclass, field, fields


@dataclass(slots=True)
class Plug:
    name: str
    package_name: str
    version: str = "@main"
    configs: dict = field(default_factory=dict)

    def __post_init__(self):
        for _field in fields(self):
            if (
                not isinstance(_field.default, _MISSING_TYPE)
                and getattr(self, _field.name) is None
            ):
                setattr(self, _field.name, _field.default)

        if not isinstance(self.name, str):
            raise ValueError("name must be a string")
        if not isinstance(self.package_name, str):
            raise ValueError("package_name must be a string")
        if not isinstance(self.version, str):
            raise ValueError("version must be a string")
        if not isinstance(self.configs, dict):
            raise ValueError("configs must be a dictionary")
