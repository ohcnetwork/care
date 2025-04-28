from care.emr.reports.renderer.base import Renderer


class RendererRegistry:
    """
    A global registry mapping renderer names to RendererRegistry subclasses.
    You can seed built-ins at import time and add plugins later via .register().
    """

    _renderers: dict[str, type[Renderer]] = {}

    @classmethod
    def register(cls, render_format: str, renderer: type[Renderer]) -> None:
        """
        Register or override a renderer handler for the given renderer name.
        """
        cls._renderers[render_format] = renderer

    @classmethod
    def get(cls, render_format: str) -> type[Renderer] | None:
        """
        Lookup a handler by its renderer name, or return None if not found.
        """
        return cls._renderers.get(render_format)

    @classmethod
    def all(cls) -> dict[str, type[Renderer]]:
        """
        Return a copy of the full registry.
        """
        return cls._renderers.copy()
