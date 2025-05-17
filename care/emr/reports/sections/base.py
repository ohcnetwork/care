from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from django.db.models import QuerySet

if TYPE_CHECKING:
    from collections.abc import Callable


from care.emr.reports.renderer.base import Renderer


class BaseSection(ABC):
    __model__ = None

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
        count = self.opts.get("count")

        if not isinstance(qs, QuerySet):
            return qs

        if filters:
            qs = qs.filter(**{f"{k}__in": v for k, v in filters.items() if v})
        if count:
            qs = qs[:count]
        return qs

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

    def render_list(self, qs):
        fields = self.get_fields() or []
        rows = []
        for obj in qs:
            rows.append(
                [
                    [f.replace("_", " ").title(), self.extract_value(obj, f)]
                    for f in fields
                ]
            )
        return self.renderer.render_list(self.opts.get("title", ""), rows)

    def render_text(self, qs):
        fields = self.get_fields() or []
        separator = self.opts.get("separator", None)
        if separator is None:
            separator = ", "

        values = []

        for obj in qs:
            parts = [
                str(self.extract_value(obj, field))
                for field in fields
                if self.extract_value(obj, field)
            ]
            combined_text = separator.join(parts).strip()
            if combined_text:
                values.append(combined_text)

        return self.renderer.render_text(self.opts.get("title", ""), values)

    def render_non_table(self, qs):
        style = self.opts.get("style", "list")
        if style == "list":
            return self.render_list(qs)
        if style == "text":
            return self.render_text(qs)
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

    def get_valid_filters(self):
        # TODO: Need to be improved , maybe we can add specific filters for each sections like we have for fields

        model = getattr(self, "__model__", None)
        if not model:
            return []

        excluded = {
            "id",
            "external_id",
            "created_date",
            "modified_date",
            "deleted",
            "meta",
            "created_by",
            "updated_by",
        }

        return sorted(
            [
                field.name
                for field in model._meta.get_fields()  # noqa SLF001
                if field.name not in excluded
                and not (field.is_relation and field.many_to_one)
                and not field.auto_created
            ]
        )
