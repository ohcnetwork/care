from django.core import exceptions
from django.db import models

from .ulid import ULID


class ULIDField(models.Field):
    description = "Universally Unique Lexicographically Sortable Identifier"
    empty_strings_allowed = False

    def __init__(self, verbose_name=None, **kwargs):
        kwargs.setdefault("max_length", 26)  # default length of ulid
        super().__init__(verbose_name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def get_internal_type(self) -> str:
        return "CharField"

    def get_db_prep_value(self, value, connection, prepared=False) -> str | None:
        if value is None:
            return None
        if not isinstance(value, ULID):
            value = self.to_python(value)
        return str(value)

    def from_db_value(self, value, expression, connection) -> ULID | None:
        return self.to_python(value)

    def to_python(self, value) -> ULID | None:
        if value is None:
            return None
        try:
            return ULID.parse(value)
        except (AttributeError, ValueError) as e:
            raise exceptions.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            ) from e
