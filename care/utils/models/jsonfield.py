# Reference: https://medium.com/@philamersune/using-postgresql-jsonfield-in-sqlite-95ad4ad2e5f1
import json

from django.conf import settings
from django.contrib.postgres.fields import ArrayField as DjangoArrayField
from django.contrib.postgres.fields import JSONField as DjangoJSONField
from django.db.models import Field

if "spatialite" in settings.DATABASES["default"]["ENGINE"]:

    class JSONField(Field):
        def db_type(self, connection):
            return "text"

        def from_db_value(self, value, expression, connection):
            if value is not None:
                return self.to_python(value)
            return value

        def to_python(self, value):
            if value is not None:
                try:
                    return json.loads(value)
                except (TypeError, ValueError):
                    return value
            return value

        def get_prep_value(self, value):
            if value is not None:
                return str(json.dumps(value))
            return value

        def value_to_string(self, obj):
            return self.value_from_object(obj)

    class ArrayField(JSONField):
        def __init__(self, base_field, size=None, **kwargs):
            """Care for DjangoArrayField's kwargs."""
            self.base_field = base_field
            self.size = size
            super().__init__(**kwargs)

        def deconstruct(self):
            """Need to create migrations properly."""
            name, path, args, kwargs = super().deconstruct()
            kwargs.update(
                {"base_field": self.base_field.clone(), "size": self.size,}
            )
            return name, path, args, kwargs


else:

    class JSONField(DjangoJSONField):
        pass

    class ArrayField(DjangoArrayField):
        pass
