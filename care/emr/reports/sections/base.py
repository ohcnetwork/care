import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from django.db.models import QuerySet

if TYPE_CHECKING:
    from collections.abc import Callable

from care.emr.reports.renderer.base import Renderer


class BaseSection(ABC):
    DEFAULT_EMPTY = "-"

    def __init__(self, config: dict, context: dict, renderer: Renderer):
        self.is_table = config["is_table"]
        self.opts = config["options"]
        self.context = context
        self.renderer = renderer
        self.field_extractors: dict[str, Callable[[Any], Any]] = {}

    @abstractmethod
    def fetch_data(self):
        pass

    def filter_data(self, qs):
        filters = self.opts.get("filters", {})
        if not filters or not isinstance(qs, QuerySet):
            return qs
        return qs.filter(**{f"{k}__in": v for k, v in filters.items() if v})

    def get_fields(self):
        return self.opts.get("columns") if self.is_table else self.opts.get("fields")

    def extract_value(self, obj, field: str):
        logging.warning("Extracting value for field: %s", field)
        if field in self.field_extractors:
            logging.warning("Extracting extractor for field: %s", field)
            logging.warning("Extractor: %s", self.field_extractors[field])
            logging.warning("Object: %s", obj.created_by)
            val = self.field_extractors[field](obj)
        else:
            val = getattr(obj, field, None)
        return val if val not in (None, "") else self.DEFAULT_EMPTY

    def build_table_rows(self, qs):
        rows = []
        for obj in qs:
            rows.append([self.extract_value(obj, f) for f in self.get_fields() or []])
        return rows

    def render_table(self, qs):
        columns = [f.replace("_", " ").title() for f in self.get_fields()]
        rows = self.build_table_rows(qs)
        title = self.opts.get("title", "")
        return self.renderer.render_table(title, columns, rows)

    def render_list(self, obj):
        fields = self.get_fields() or []
        title = self.opts.get("title", "")
        rows = [
            [f.replace("_", " ").title(), self.extract_value(obj, f)] for f in fields
        ]
        return self.renderer.render_list(title, rows)

    def render_text(self, obj):
        fields = self.get_fields() or []
        title = self.opts.get("title", "")
        text_field = fields[0] if fields else ""
        text_value = self.extract_value(obj, text_field) if text_field else ""
        return self.renderer.render_text(title, text_value)

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
        if self.is_table:
            return self.render_table(data)
        return self.render_non_table(data)
