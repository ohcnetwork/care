from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Field:
    DEFAULT_NONE_VALUE = ""

    def __init__(
        self,
        key: str,
        display: str,
        mapping: str | Callable,
        preview_value: Any,
        description: str = "",
        field_type: str = "string",
    ):
        self.key = key
        self.display = display
        self.mapping = mapping
        self.preview_value = preview_value
        self.description = description
        self.type = field_type

    def to_dict(self):
        if isinstance(self.preview_value, (list, dict)):
            preview_value = self.preview_value
        elif self.preview_value is not None:
            preview_value = str(self.preview_value)
        else:
            preview_value = ""

        return {
            "key": self.key,
            "display": self.display,
            "type": self.type,
            "preview_value": preview_value,
            "description": self.description,
        }

    def get_value(self, obj):
        if isinstance(self.mapping, str):
            value = getattr(obj, self.mapping, None)
        elif callable(self.mapping):
            value = self.mapping(obj)
        else:
            value = None

        if value is None:
            return self.DEFAULT_NONE_VALUE

        if isinstance(value, (list, dict)):
            return value

        return str(value)


class BaseContextBuilder(ABC):
    model = None
    fields: list[Field] = []
    allowed_filters: list = []
    depends_on: list[str] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._field_registry = {}
        cls._registry_initialized = False

    @classmethod
    def register_field(cls, field: Field, override: bool = False):
        if not cls._registry_initialized:
            cls._initialize_registry()

        if field.key in cls._field_registry and not override:
            msg = f"Field '{field.key}' already registered for {cls.__name__}. Use override=True to replace."
            raise ValueError(msg)

        cls._field_registry[field.key] = field

    @classmethod
    def _initialize_registry(cls):
        if cls._registry_initialized:
            return

        for field in cls.fields:
            cls._field_registry[field.key] = field

        cls._registry_initialized = True

    @classmethod
    def get_registered_fields(cls) -> list[Field]:
        if not cls._registry_initialized:
            cls._initialize_registry()

        field_order = []
        seen_keys = set()

        for field in cls.fields:
            if field.key in cls._field_registry:
                field_order.append(cls._field_registry[field.key])
                seen_keys.add(field.key)

        for key, field in cls._field_registry.items():
            if key not in seen_keys:
                field_order.append(field)

        return field_order

    @classmethod
    def unregister_field(cls, field_key: str):
        if not cls._registry_initialized:
            cls._initialize_registry()

        if field_key in cls._field_registry:
            del cls._field_registry[field_key]

    @classmethod
    def clear_field_registry(cls):
        cls._field_registry.clear()
        cls._registry_initialized = False
        cls._initialize_registry()

    @classmethod
    def get_allowed_filter_names(cls) -> list[str]:
        filter_names = []
        for filter_field in cls.allowed_filters:
            if hasattr(filter_field, "field"):
                filter_names.append(filter_field.field.name)
            else:
                model_name = cls.model.__name__ if cls.model else "Model"
                msg = (
                    f"Invalid filter in {cls.__name__}.allowed_filters: {filter_field!r}. "
                    f"Must be Django field object (e.g., {model_name}.field_name)."
                )
                raise ValueError(msg)

        return filter_names

    @classmethod
    def validate_allowed_filters(cls) -> bool:
        if not cls.allowed_filters:
            return True

        cls.get_allowed_filter_names()
        return True

    @classmethod
    def get_schema(cls):
        return {
            "display": cls.get_display_name(),
            "description": cls.get_description(),
            "fields": [field.to_dict() for field in cls.get_registered_fields()],
            "allowed_filters": cls.get_allowed_filter_names(),
            "depends_on": cls.depends_on,
        }

    @classmethod
    def _build_context_from_object(
        cls, obj, requested_fields: list[str] | None = None
    ) -> dict:
        context = {}
        registered_fields = cls.get_registered_fields()

        if requested_fields is None:
            requested_fields = [field.key for field in registered_fields]

        valid_keys = {field.key for field in registered_fields}
        for field_key in requested_fields if requested_fields is not None else []:
            if field_key not in valid_keys:
                msg = f"Invalid field '{field_key}' for {cls.get_display_name()}"
                raise ValueError(msg)

        for field in registered_fields:
            if field.key in requested_fields:
                context[field.key] = field.get_value(obj)

        return context

    @classmethod
    @abstractmethod
    def get_display_name(cls) -> str:
        pass

    @classmethod
    def get_description(cls) -> str:
        return ""


class SingleObjectContextBuilder(BaseContextBuilder):
    @classmethod
    def get_context(cls, ctx: dict, requested_fields: list[str] | None = None) -> dict:
        obj = cls.get_object(ctx)
        return cls._build_context_from_object(obj, requested_fields)

    @classmethod
    @abstractmethod
    def get_object(cls, ctx: dict):
        pass


class QuerysetContextBuilder(BaseContextBuilder):
    base_filters: dict = {}

    @classmethod
    def get_queryset(cls, ctx: dict):
        raise NotImplementedError("Subclasses must implement get_queryset method")

    @classmethod
    def build_list_context(
        cls,
        ctx: dict,
        filters: dict | None = None,
        limit: int | None = None,
        requested_fields: list[str] | None = None,
    ):
        queryset = cls.get_queryset(ctx)

        if filters:
            queryset = queryset.filter(**filters)

        if limit is not None and 0 < limit < queryset.count():
            queryset = queryset[:limit]

        return [
            cls._build_context_from_object(obj, requested_fields) for obj in queryset
        ]
