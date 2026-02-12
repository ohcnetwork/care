from typing import Any

from care.emr.reports.renderer.generators.base import BaseOutputGenerator


class GeneratorRegistry:
    _registry: dict[str, type[BaseOutputGenerator]] = {}
    _format_config: dict[str, dict[str, str]] = {}

    @classmethod
    def register(
        cls,
        format_type: str,
        generator_class: type[BaseOutputGenerator],
        mime_type: str,
        file_extension: str,
    ) -> None:
        if not format_type or not isinstance(format_type, str):
            raise ValueError("format_type must be a non-empty string")

        if not mime_type or not isinstance(mime_type, str):
            raise ValueError("mime_type must be a non-empty string")

        if not file_extension or not isinstance(file_extension, str):
            raise ValueError("file_extension must be a non-empty string")

        if not issubclass(generator_class, BaseOutputGenerator):
            err = f"Generator class must be a subclass of BaseOutputGenerator, got {generator_class.__name__}"
            raise TypeError(err)

        format_type = format_type.lower()
        cls._registry[format_type] = generator_class
        cls._format_config[format_type] = {
            "mime_type": mime_type,
            "file_extension": file_extension,
        }

    @classmethod
    def get(cls, format_type: str) -> type[BaseOutputGenerator]:
        format_type = format_type.lower()
        if format_type not in cls._registry:
            available = ", ".join(cls.get_all_formats())
            error = f"No generator registered for format '{format_type}'. Available formats: {available}"
            raise KeyError(error)
        return cls._registry[format_type]

    @classmethod
    def get_format_config(cls, format_type: str) -> dict[str, str]:
        format_type = format_type.lower()
        if format_type not in cls._format_config:
            available = ", ".join(cls.get_all_formats())
            err = (
                f"No format config for '{format_type}'. Available formats: {available}"
            )
            raise KeyError(err)
        return cls._format_config[format_type].copy()

    @classmethod
    def is_registered(cls, format_type: str) -> bool:
        return format_type.lower() in cls._registry

    @classmethod
    def get_all_formats(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def get_all_generators(cls) -> dict[str, type[BaseOutputGenerator]]:
        return cls._registry.copy()

    @classmethod
    def get_schema(cls) -> dict[str, dict[str, Any]]:
        schema = {}
        for format_type, generator_class in cls._registry.items():
            try:
                generator = generator_class()
                supported_options = generator.get_supported_options()
            except Exception:
                supported_options = {}

            format_config = cls._format_config.get(format_type, {})
            schema[format_type] = {
                "format": format_type,
                "generator": generator_class.__name__,
                "mime_type": format_config.get("mime_type"),
                "file_extension": format_config.get("file_extension"),
                "supported_options": supported_options,
            }
        return schema

    @classmethod
    def unregister(cls, format_type: str) -> None:
        format_type = format_type.lower()
        if format_type in cls._registry:
            del cls._registry[format_type]
        if format_type in cls._format_config:
            del cls._format_config[format_type]

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
        cls._format_config.clear()
