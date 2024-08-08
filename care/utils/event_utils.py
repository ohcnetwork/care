from datetime import datetime
from json import JSONEncoder
from logging import getLogger

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, Model
from multiselectfield.db.fields import MSFList, MultiSelectField

logger = getLogger(__name__)


def is_null(data):
    return data is None or data == ""


def get_changed_fields(old: Model, new: Model) -> set[str]:
    changed_fields: set[str] = set()
    for field in new._meta.fields:
        field_name = field.name
        if isinstance(field, MultiSelectField):
            old_val = set(getattr(old, field_name, []))
            new_val = set(map(str, getattr(new, field_name, [])))
            if old_val != new_val:
                changed_fields.add(field_name)
        elif getattr(old, field_name, None) != getattr(new, field_name, None):
            changed_fields.add(field_name)
    return changed_fields


def serialize_field(object: Model, field_name: str):
    if "__" in field_name:
        field_name, sub_field = field_name.split("__", 1)
        related_object = getattr(object, field_name)
        return serialize_field(related_object, sub_field)

    field = None
    try:
        field = object._meta.get_field(field_name)
    except FieldDoesNotExist as e:
        try:
            # try to get property field
            return getattr(object, field_name)
        except AttributeError:
            raise e

    value = getattr(object, field.name, None)
    if issubclass(field.__class__, Field) and field.choices:
        # serialize choice fields with display value
        return getattr(object, f"get_{field.name}_display", lambda: value)()
    return value


def model_diff(old, new):
    diff = {}
    for field in new._meta.fields:
        field_name = field.name
        if isinstance(field, MultiSelectField):
            old_val = set(getattr(old, field_name, []))
            new_val = set(map(str, getattr(new, field_name, [])))
            if old_val != new_val:
                diff[field_name] = new_val
            continue
        if getattr(old, field_name, None) != getattr(new, field_name, None):
            diff[field_name] = getattr(new, field_name, None)

    return diff


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, MSFList):
            return list(map(str, o))
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime):
            return o.isoformat()
        logger.warning(f"Serializing Unknown Type {type(o)}, {o}")
        return str(o)
