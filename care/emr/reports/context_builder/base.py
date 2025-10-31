from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Field:
    """Field definition with mapping built-in"""

    DEFAULT_NONE_VALUE = ""

    def __init__(
        self,
        key: str,
        display: str,
        mapping: str | Callable,
        preview_value: Any,
        description: str = "",
    ):
        self.key = key
        self.display = display
        self.mapping = mapping
        self.preview_value = preview_value
        self.description = description

    def to_dict(self):
        """Convert to JSON-serializable dict for schema API"""
        return {
            "key": self.key,
            "display": self.display,
            "preview_value": str(self.preview_value)
            if self.preview_value is not None
            else "",
            "description": self.description,
        }

    def get_value(self, obj):
        """Get real value from model instance using mapping"""
        if isinstance(self.mapping, str):
            value = getattr(obj, self.mapping, None)
        elif callable(self.mapping):
            value = self.mapping(obj)
        else:
            value = None

        return str(value) if value is not None else self.DEFAULT_NONE_VALUE


class BaseContextBuilder(ABC):
    """
    Abstract base class for all context builders.
    """

    model = None
    fields: list[Field] = []

    @classmethod
    def get_schema(cls):
        """Return schema for this builder (for frontend)"""
        return {
            "display": cls.get_display_name(),
            "description": cls.get_description(),
            "fields": [field.to_dict() for field in cls.fields],
        }

    @classmethod
    def _build_context_from_object(
        cls, obj, requested_fields: list[str] | None = None
    ) -> dict:
        context = {}

        if requested_fields is None:
            requested_fields = [field.key for field in cls.fields]

        valid_keys = {field.key for field in cls.fields}
        for field_key in requested_fields if requested_fields is not None else []:
            if field_key not in valid_keys:
                msg = f"Invalid field '{field_key}' for {cls.get_display_name()}"
                raise ValueError(msg)

        for field in cls.fields:
            if field.key in requested_fields:
                context[field.key] = field.get_value(obj)

        return context

    @classmethod
    @abstractmethod
    def get_display_name(cls) -> str:
        """Return human-readable name for this context builder"""

    @classmethod
    def get_description(cls) -> str:
        """Return description of this context builder"""
        return ""


class SingleObjectContextBuilder(BaseContextBuilder):
    """
    Base class for single object builders (Patient, Encounter, etc.).
    """

    @classmethod
    def get_context(cls, ctx: dict, requested_fields: list[str] | None = None) -> dict:
        """
        Build context from ctx dictionary.

        Args:
            ctx: Context dictionary containing available data
            requested_fields: List of field keys to include (if None, include all)

        Returns:
            Dictionary with field_key: value pairs
        """
        obj = cls.get_object(ctx)
        return cls._build_context_from_object(obj, requested_fields)

    @classmethod
    @abstractmethod
    def get_object(cls, ctx: dict):
        """
        Get the model instance from ctx.

        Args:
            ctx: Context dictionary containing available data

        Returns:
            Model instance

        Raises:
            ValueError: If required data is not available in ctx
        """


class QuerysetContextBuilder(BaseContextBuilder):
    """
    Base class for builders that work with querysets (lists).
    These are used for diagnoses, symptoms, medications, etc.

    The ctx dict should contain either 'encounter' or 'encounter_id'.
    """

    # Use this to apply default filters to the queryset
    base_filters: dict = {}

    @classmethod
    def get_queryset(cls, ctx: dict):
        """
        Get queryset based on context.

        Args:
            ctx: Context dictionary containing 'encounter', 'encounter_id', 'patient', or 'patient_id'

        Returns:
            QuerySet of related objects
        """
        raise NotImplementedError("Subclasses must implement get_queryset method")

    @classmethod
    def build_list_context(
        cls,
        ctx: dict,
        filters: dict | None = None,
        limit: int | None = None,
        requested_fields: list[str] | None = None,
    ):
        """
        Build context for a list of objects.

        Args:
            ctx: Context dictionary containing 'encounter' or 'encounter_id'
            filters: Additional Django ORM filters to apply
            limit: Maximum number of items to return
            requested_fields: Fields to include for each item

        Returns:
            List of context dictionaries
        """
        queryset = cls.get_queryset(ctx)

        if filters:
            queryset = queryset.filter(**filters)

        if limit is not None and 0 < limit < queryset.count():
            queryset = queryset[:limit]

        return [
            cls._build_context_from_object(obj, requested_fields) for obj in queryset
        ]
