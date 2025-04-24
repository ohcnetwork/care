from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from django.db.models import QuerySet
from django.template.loader import render_to_string


class BaseSection(ABC):
    DEFAULT_EMPTY = "-"

    def __init__(self, config: dict, context: dict):
        self.is_table = config["is_table"]
        self.opts = config["options"]
        self.context = context
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
        if field in self.field_extractors:
            val = self.field_extractors[field](obj)
        else:
            val = getattr(obj, field, None)
        return val if val not in (None, "") else self.DEFAULT_EMPTY

    def build_table_rows(self, qs):
        rows = []
        for obj in qs:
            rows.append([self.extract_value(obj, f) for f in self.get_fields() or []])
        return rows

    def render_list(self, qs):
        fields = self.get_fields() or []
        style = self.opts.get("style", "list")
        title = self.opts.get("title", "")
        obj = qs[0]
        if style == "list":
            rows = [
                [f.replace("_", " ").title(), self.extract_value(obj, f)]
                for f in fields
            ]
            return render_to_string(
                "reports/typst/list.typ", {"title": title, "rows": rows}
            )
        # plain-text mode
        text_field = fields[0]
        text_value = self.extract_value(obj, text_field)
        return render_to_string(
            "reports/typst/text.typ", {"title": title, "text": text_value}
        )

    def render_table(self, qs):
        columns = [f.replace("_", " ").title() for f in self.get_fields()]
        rows = self.build_table_rows(qs)
        return render_to_string(
            "reports/typst/table.typ",
            {
                "title": self.opts.get("title", ""),
                "columns": columns,
                "rows": rows,
            },
        )

    def render(self) -> str:
        raw = self.fetch_data() or []
        data = self.filter_data(raw)
        if not data:
            return ""
        return self.render_table(data) if self.is_table else self.render_list(data)
