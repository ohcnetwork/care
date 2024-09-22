from datetime import datetime
from json import JSONEncoder
from logging import getLogger

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, Model

logger = getLogger(__name__)


def is_null(data):
    return data is None or data == ""


def get_changed_fields(old: Model, new: Model) -> set[str]:
    changed_fields: set[str] = set()
    for field in new._meta.fields:
        field_name = field.name
        if getattr(old, field_name, None) != getattr(new, field_name, None):
            changed_fields.add(field_name)
    return changed_fields


def serialize_field(object: Model, field_name: str):
    if "__" in field_name:
        field_name, sub_field = field_name.split("__", 1)
        related_object = getattr(object, field_name, None)
        return serialize_field(related_object, sub_field)

    value = None
    try:
        value = getattr(object, field_name)
    except AttributeError:
        if object is not None:
            logger.warning(
                f"Field {field_name} not found in {object.__class__.__name__}"
            )
        return None

    try:
        # serialize choice fields with display value
        field = object._meta.get_field(field_name)
        if issubclass(field.__class__, Field) and field.choices:
            value = getattr(object, f"get_{field_name}_display", lambda: value)()
    except FieldDoesNotExist:
        # the required field is a property and not a model field
        pass

    return value


def model_diff(old, new):
    diff = {}
    for field in new._meta.fields:
        field_name = field.name
        if getattr(old, field_name, None) != getattr(new, field_name, None):
            diff[field_name] = getattr(new, field_name, None)

    return diff


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime):
            return o.isoformat()
        logger.warning(f"Serializing Unknown Type {type(o)}, {o}")
        return str(o)
