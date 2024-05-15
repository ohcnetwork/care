from datetime import datetime
from json import JSONEncoder
from logging import getLogger

from django.core.serializers import serialize
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


def serialize_field(object: Model, field: Field):
    value = getattr(object, field.name)
    if isinstance(value, Model):
        # serialize the fields of the related model
        return serialize("python", [value])[0]["fields"]
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
