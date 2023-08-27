from typing import Iterable, List

import jsonschema
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible


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
        self,
        errors: Iterable[jsonschema.ValidationError],
        container: List[ValidationError],
    ):
        for error in errors:
            if error.context:
                return self._extract_errors(error.context, container)

            message = str(error).replace("\n\n", ": ").replace("\n", "")
            container.append(ValidationError(message))


@deconstructible
class PhoneNumberValidator(RegexValidator):
    """
    Any one of the specified types of phone numbers are considered valid.

    Allowed types:
    - `mobile` (Indian XOR International)
    - `indian_mobile` (Indian only)
    - `international_mobile` (International only)
    - `landline` (Indian only)
    - `support` (Indian only)

    Example usage:

    ```
    field = models.CharField(
        validators=[PhoneNumberValidator(types=("mobile", "landline", "support"))])
    )
    ```
    """

    indian_mobile_number_regex = r"^(?=^\+91)(^\+91[6-9]\d{9}$)"
    international_mobile_number_regex = r"^(?!^\+91)(^\+\d{1,3}\d{8,14}$)"
    landline_number_regex = r"^\+91[2-9]\d{7,9}$"
    support_number_regex = r"^(1800|1860)\d{6,7}$"

    regex_map = {
        "indian_mobile": indian_mobile_number_regex,
        "international_mobile": international_mobile_number_regex,
        "mobile": rf"{indian_mobile_number_regex}|{international_mobile_number_regex}",
        "landline": landline_number_regex,
        "support": support_number_regex,
    }

    def __init__(self, types: Iterable[str], *args, **kwargs):
        if not isinstance(types, Iterable) or isinstance(types, str) or len(types) == 0:
            raise ValueError("The `types` argument must be a non-empty iterable.")

        self.types = types
        self.message = f"Invalid phone number. Must be one of the following types: {', '.join(self.types)}. Received: %(value)s"
        self.code = "invalid_phone_number"

        self.regex = r"|".join([self.regex_map[type] for type in self.types])
        super().__init__(*args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, PhoneNumberValidator) and self.types == other.types


mobile_validator = PhoneNumberValidator(types=("mobile",))
mobile_or_landline_number_validator = PhoneNumberValidator(types=("mobile", "landline"))
