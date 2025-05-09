from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from django.db.models import QuerySet

if TYPE_CHECKING:
    from collections.abc import Callable


from care.emr.reports.renderer.base import Renderer


class BaseSection(ABC):
    DEFAULT_EMPTY = "-"

    def __init__(self, config: dict, context: dict, renderer: Renderer):
        self.is_table = config.get("is_table", False)
        self.opts = config.get("options", {})
        self.context = context
        self.renderer = renderer
        self.field_extractors: dict[str, Callable[[Any], Any]] = {}

    @abstractmethod
    def fetch_data(self):
        pass

    def register_field(self, name: str, extractor: "Callable[[Any], Any]"):
        """Manually register a field extractor."""
        self.field_extractors[name] = extractor

    def filter_data(self, qs):
        filters = self.opts.get("filters", {})
        if not filters or not isinstance(qs, QuerySet):
            return qs
        return qs.filter(**{f"{k}__in": v for k, v in filters.items() if v})

    def get_fields(self):
        return self.opts.get("columns") if self.is_table else self.opts.get("fields")

    def extract_value(self, obj, field: str):
        extractor = self.field_extractors.get(field)
        if extractor is None:
            return None
        val = extractor(obj)
        return val if val not in (None, "") else self.DEFAULT_EMPTY

    def build_table_rows(self, qs):
        return [
            [self.extract_value(obj, f) for f in self.get_fields() or []] for obj in qs
        ]

    def render_table(self, qs):
        columns = [f.replace("_", " ").title() for f in self.get_fields()]
        rows = self.build_table_rows(qs)
        return self.renderer.render_table(self.opts.get("title", ""), columns, rows)

    def render_list(self, obj):
        fields = self.get_fields() or []
        rows = [
            [f.replace("_", " ").title(), self.extract_value(obj, f)] for f in fields
        ]
        return self.renderer.render_list(self.opts.get("title", ""), rows)

    def render_text(self, obj):
        fields = self.get_fields() or []
        text_field = fields[0] if fields else ""
        text_value = self.extract_value(obj, text_field) if text_field else ""
        return self.renderer.render_text(self.opts.get("title", ""), text_value)

    def render_non_table(self, qs):
        style = self.opts.get("style", "list")
        first_obj = qs[0]
        if style == "list":
            return self.render_list(first_obj)
        if style == "text":
            return self.render_text(first_obj)
        error = f"Unknown style '{style}'"
        raise ValueError(error)

    def render(self) -> str:
        raw = self.fetch_data() or []
        data = self.filter_data(raw)
        if not data:
            return ""
        return self.render_table(data) if self.is_table else self.render_non_table(data)

    def available_fields(self) -> list[str]:
        return sorted(self.field_extractors.keys())
