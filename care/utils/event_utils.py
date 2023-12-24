from datetime import datetime
from json import JSONEncoder

from django.db import models
from multiselectfield.db.fields import MSFList, MultiSelectField


def is_null(data):
    return data is None or data == ""


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
        if isinstance(o, models.Model):
            return o.pk
        if isinstance(o, MSFList):
            return list(map(str, o))
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)
