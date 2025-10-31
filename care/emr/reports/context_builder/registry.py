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
        self._single_builders: dict[str, type[BaseContextBuilder]] = {}
        self._queryset_builders: dict[str, type[BaseContextBuilder]] = {}

    def register(self, key: str, builder_class: type[BaseContextBuilder]):
        """
        Register a context builder. Automatically detects if it's a single object
        or queryset builder by checking if it's a subclass of QuerysetContextBuilder.
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
        """Get all registered single object builders."""
        return self._single_builders.copy()

    def get_queryset_builders(self) -> dict[str, type[BaseContextBuilder]]:
        """Get all registered queryset builders."""
        return self._queryset_builders.copy()

    def get_single_builder(self, key: str) -> type[BaseContextBuilder]:
        """
        Get a specific single builder by key.

        Args:
            key: The builder key

        Returns:
            The builder class

        Raises:
            KeyError: If builder not found
        """
        if key not in self._single_builders:
            msg = f"Single builder '{key}' not found in contex_builder_registry"
            raise KeyError(msg)
        return self._single_builders[key]

    def get_queryset_builder(self, key: str) -> type[BaseContextBuilder]:
        """
        Get a specific queryset builder by key.

        Args:
            key: The builder key

        Returns:
            The builder class

        Raises:
            KeyError: If builder not found
        """
        if key not in self._queryset_builders:
            msg = f"Queryset builder '{key}' not found in contex_builder_registry"
            raise KeyError(msg)
        return self._queryset_builders[key]

    def unregister(self, key: str):
        """Unregister a builder (mainly for testing)."""
        if key in self._single_builders:
            del self._single_builders[key]
        if key in self._queryset_builders:
            del self._queryset_builders[key]

    def clear(self):
        """Clear all registrations (mainly for testing)."""
        self._single_builders.clear()
        self._queryset_builders.clear()


contex_builder_registry = ContextBuilderRegistry()
