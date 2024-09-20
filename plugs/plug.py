from dataclasses import _MISSING_TYPE, dataclass, fields


@dataclass(slots=True)
class Plug:
    name: str
    package_name: str
    version: str = "@main"
    configs: dict = {}

    def __post_init__(self) -> None:
        for field in fields(self):
            if (
                not isinstance(field.default, _MISSING_TYPE)
                and getattr(self, field.name) is None
            ):
                setattr(self, field.name, field.default)
