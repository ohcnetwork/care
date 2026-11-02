import random
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any


class Field:
    DEFAULT_NONE_VALUE = ""

    def __init__(
        self,
        display: str = "",
        preview_value: Any = None,
        preview_fn: Callable | None = None,
        mapping=None,
        target_context=None,
        description: str = "",
        field_type: str = "string",
    ):
        self.display = display
        self.mapping = mapping
        self.preview_value = preview_value
        self.description = description
        self.type = field_type
        self.target_context = target_context
        self.preview_fn = preview_fn

    def get_value(self, parent_context, parent_attribute, is_preview):  # noqa PLR0911
        if self.target_context:
            return template_value(
                self.target_context(
                    parent_context, parent_attribute, is_preview=is_preview
                )
            )

        if is_preview:
            if self.preview_value is not None:
                return template_value(self.preview_value)
            if self.preview_fn:
                return template_value(self.preview_fn())
            return self.DEFAULT_NONE_VALUE

        if isinstance(self.mapping, str):
            value = getattr(parent_context, self.mapping, None)
        elif callable(self.mapping):
            value = self.mapping(parent_context)
        else:
            value = getattr(parent_context, parent_attribute, None)

        if value is None:
            return self.DEFAULT_NONE_VALUE

        if isinstance(value, (list, dict)):
            return template_value(value)

        return str(value)


class ContextBuilderBase:
    __context_type__ = ""
    standalone_context = False
    context_key = ""
    # Standalone Contexts are contexts which can generate their own reports
    __slug__ = ""
    __display_name__ = ""
    __description__ = ""
    # Used to identify the right context

    def __init__(
        self, parent_context=None, parent_attribute=None, context=None, is_preview=None
    ):
        self.parent_context = parent_context
        self.parent_attribute = parent_attribute
        if context is None and not bool(is_preview):
            context = self.get_context()
        self.context = context
        self.is_preview = bool(is_preview)

    def get_context(self):
        return self.parent_context

    def __getattribute__(self, name: str) -> Any:
        val = super().__getattribute__(name)
        if val and isinstance(val, Field):
            return val.get_value(self.context, name, self.is_preview)
        return val

    def get_iterable(self, qs):
        return iter(self.__class__(context=c, is_preview=self.is_preview) for c in qs)

    def filter(self, **kwargs):
        if self.is_preview:
            limit = kwargs.get("limit", 4)
            return [
                self.__class__(is_preview=True)
                for c in range(random.randint(1, limit))  # noqa S311
            ]
        return self._filter(**kwargs)


class QuerysetContextBuilder(ContextBuilderBase):
    __context_type__ = "queryset"

    filterset_class = None
    __filterset_backends__ = []

    def __iter__(self):
        if self.is_preview:
            return iter(
                self.__class__(is_preview=True)
                for _ in range(random.randint(1, 4))  # noqa: S311
            )
        return self.get_iterable(self.context)

    def perform_extra_filters(self, qs, **kwargs):
        return qs

    def _filter(self, **kwargs):
        qs = self.context
        for filterset_class in self.__filterset_backends__:
            qs = filterset_class().filter_queryset(
                SimpleNamespace(query_params=kwargs), qs, self
            )
        qs = self.perform_extra_filters(qs, **kwargs)
        if "limit" in kwargs:
            qs = qs[: kwargs["limit"]]
        return self.get_iterable(qs)


class SingleObjectContextBuilder(ContextBuilderBase):
    __context_type__ = "single_object"


class ListContextBuilder(ContextBuilderBase):
    __context_type__ = "list"


def template_value(value):
    """Copy report data without exposing objects hidden inside JSON-like values."""
    if value is None or type(value) in (str, bool, int, float, date, datetime, Decimal):
        return value
    if isinstance(value, ContextBuilderBase):
        return value
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError("Report data must have string dictionary keys")
        return {key: template_value(item) for key, item in value.items()}
    if type(value) in (list, tuple):
        return [template_value(item) for item in value]
    raise TypeError("Report data contains an unsupported object")
