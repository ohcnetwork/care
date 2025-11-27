from care.emr.reports.context_builder.base import (
    BaseContextBuilder,
    QuerysetContextBuilder,
    SingleObjectContextBuilder,
)


class ContextBuilderRegistry:
    """
    Registry for managing context builders.
    """

    def __init__(self):
        self._single_builders: dict[str, type[SingleObjectContextBuilder]] = {}
        self._queryset_builders: dict[str, type[QuerysetContextBuilder]] = {}

    def register(self, key: str, builder_class: type[BaseContextBuilder]):
        """
        Register a context builder
        """
        if not issubclass(builder_class, BaseContextBuilder):
            raise TypeError("Builder must be a subclass of BaseContextBuilder")

        if issubclass(builder_class, QuerysetContextBuilder):
            if key in self._queryset_builders:
                msg = f"Queryset builder with key '{key}' is already registered"
                raise ValueError(msg)
            self._queryset_builders[key] = builder_class
        elif issubclass(builder_class, SingleObjectContextBuilder):
            if key in self._single_builders:
                msg = f"Single builder with key '{key}' is already registered"
                raise ValueError(msg)
            self._single_builders[key] = builder_class
        else:
            raise TypeError(
                "Builder must be a subclass of SingleObjectContextBuilder or QuerysetContextBuilder"
            )

    def get_single_builders(self) -> dict[str, type[BaseContextBuilder]]:
        """Get all registered single object builders"""
        return self._single_builders.copy()

    def get_queryset_builders(self) -> dict[str, type[BaseContextBuilder]]:
        """Get all registered queryset builders."""
        return self._queryset_builders.copy()

    def get_single_builder(self, key: str) -> type[BaseContextBuilder]:
        """
        Get a specific single builder by key
        """
        if key not in self._single_builders:
            msg = f"Single builder '{key}' not found in context_builder_registry"
            raise KeyError(msg)
        return self._single_builders[key]

    def get_queryset_builder(self, key: str) -> type[BaseContextBuilder]:
        """
        Get a specific queryset builder by key.
        """
        if key not in self._queryset_builders:
            msg = f"Queryset builder '{key}' not found in context_builder_registry"
            raise KeyError(msg)
        return self._queryset_builders[key]

    def unregister(self, key: str):
        """Unregister a builder"""
        if key in self._single_builders:
            del self._single_builders[key]
        if key in self._queryset_builders:
            del self._queryset_builders[key]

    def clear(self):
        """Clear all registrations"""
        self._single_builders.clear()
        self._queryset_builders.clear()


context_builder_registry = ContextBuilderRegistry()
