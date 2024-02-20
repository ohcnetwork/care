from django.utils.translation import gettext as _
from rest_framework import fields

from .ulid import ULID


class ULIDField(fields.Field):
    default_error_messages = {
        "invalid": _('"{value}" is not a valid ULID.'),
    }

    def to_internal_value(self, data) -> ULID:
        try:
            return ULID.parse(data)
        except (AttributeError, ValueError):
            self.fail("invalid", value=data)

    def to_representation(self, value) -> str:
        return str(ULID.parse(value))
