from care.emr.reports.sections.base import BaseSection


class SectionRegistry:
    """
    A global registry mapping source names to BaseSection subclasses.
    You can seed built-ins at import time and add plugins later via .register().
    """

    _handlers: dict[str, type[BaseSection]] = {}

    @classmethod
    def register(cls, source: str, handler: type[BaseSection]) -> None:
        """
        Register or override a section handler for the given source name.
        """
        cls._handlers[source] = handler

    @classmethod
    def get(cls, source: str) -> type[BaseSection] | None:
        """
        Lookup a handler by its source name, or return None if not found.
        """
        return cls._handlers.get(source)

    @classmethod
    def all(cls) -> dict[str, type[BaseSection]]:
        """
        Return a copy of the full registry.
        """
        return cls._handlers.copy()
