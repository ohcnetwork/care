from django.db import models

from care.emr.reports.authorizers.base import BaseReportAuthorizer


class ReportTypeConfig:
    def __init__(
        self,
        key: str,
        display_name: str,
        associating_model: type[models.Model],
        authorizer_class: type[BaseReportAuthorizer],
        description: str = "",
    ):
        self.key = key
        self.display_name = display_name
        self.associating_model = associating_model
        self.authorizer_class = authorizer_class
        self.description = description


class ReportTypeRegistry:
    _registry: dict[str, ReportTypeConfig] = {}

    @classmethod
    def register(
        cls,
        key: str,
        display_name: str,
        associating_model: type[models.Model],
        authorizer_class: type[BaseReportAuthorizer],
        description: str = "",
    ) -> None:
        if key in cls._registry:
            msg = f"Report type '{key}' is already registered"
            raise ValueError(msg)

        if not issubclass(authorizer_class, BaseReportAuthorizer):
            msg = "Authorizer must be a subclass of BaseReportAuthorizer"
            raise ValueError(msg)

        config = ReportTypeConfig(
            key=key,
            display_name=display_name,
            associating_model=associating_model,
            authorizer_class=authorizer_class,
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
                "authorizer": config.authorizer_class.__name__,
            }
        return schema

    @classmethod
    def unregister(cls, key: str) -> None:
        if key in cls._registry:
            del cls._registry[key]

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
