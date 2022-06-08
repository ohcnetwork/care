from typing import Iterable, List

import jsonschema
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class JSONFieldSchemaValidator:
    """
    Based on the JSON Schema Validator at https://github.com/wblxyxolbkhv/django-json-field-schema-validator
    """

    def __init__(self, schema: dict):
        self.schema = schema
        self.schema_validator_class = jsonschema.Draft7Validator

    def __call__(self, value):
        errors = self.schema_validator_class(self.schema).iter_errors(value)

        django_errors = []
        self._extract_errors(errors, django_errors)
        if django_errors:
            raise ValidationError(django_errors)

        return value

    def __eq__(self, other):
        if not hasattr(other, "deconstruct"):
            return False
        return self.deconstruct() == other.deconstruct()

    def _extract_errors(
        self, errors: Iterable[jsonschema.ValidationError], container: List[ValidationError],
    ):
        for error in errors:
            if error.context:
                return self._extract_errors(error.context, container)

            message = str(error).replace("\n\n", ": ").replace("\n", "")
            container.append(ValidationError(message))
