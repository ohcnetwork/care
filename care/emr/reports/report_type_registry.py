from collections.abc import Callable

from django.db import models


class ReportTypeConfig:
    def __init__(
        self,
        key: str,
        display_name: str,
        associating_model: type[models.Model],
        validator: Callable[[str], models.Model] | None = None,
        description: str = "",
    ):
        self.key = key
        self.display_name = display_name
        self.associating_model = associating_model
        self.validator = validator
        self.description = description


class ReportTypeRegistry:
    _registry: dict[str, ReportTypeConfig] = {}

    @classmethod
    def register(
        cls,
        key: str,
        display_name: str,
        associating_model: type[models.Model],
        validator: Callable[[str], models.Model] | None = None,
        description: str = "",
    ) -> None:
        if key in cls._registry:
            msg = f"Report type '{key}' is already registered"
            raise ValueError(msg)

        config = ReportTypeConfig(
            key=key,
            display_name=display_name,
            associating_model=associating_model,
            validator=validator,
            description=description,
        )
        cls._registry[key] = config

    @classmethod
    def get(cls, key: str) -> ReportTypeConfig:
        if key not in cls._registry:
            msg = (
                f"Report type '{key}' not found. "
                f"Available types: {', '.join(cls.get_all_keys())}"
            )
            raise KeyError(msg)
        return cls._registry[key]

    @classmethod
    def get_all_keys(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def get_all_configs(cls) -> dict[str, ReportTypeConfig]:
        return cls._registry.copy()

    @classmethod
    def get_schema(cls) -> dict:
        schema = {}
        for key, config in cls._registry.items():
            schema[key] = {
                "display_name": config.display_name,
                "description": config.description,
                "associating_model": config.associating_model.__name__,
            }
        return schema

    @classmethod
    def unregister(cls, key: str) -> None:
        if key in cls._registry:
            del cls._registry[key]

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
