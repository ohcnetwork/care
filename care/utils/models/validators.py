import re
from typing import Iterable, List

import jsonschema
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
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
class UsernameValidator(validators.RegexValidator):
    regex = r"^(?!.*[._-]{2})[a-z0-9](?:[a-z0-9._-]{2,14}[a-z0-9])$"
    message = _(
        "Username must be 4 to 16 characters long. "
        "It may only contain lowercase alphabets, numbers, underscores, hyphens and dots. "
        "It shouldn't start or end with underscores, hyphens or dots. "
        "It shouldn't contain consecutive underscores, hyphens or dots."
    )
    flags = re.ASCII


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


@deconstructible
class DenominationValidator:
    """
    This validator is used to validate string inputs with denominations.
    for example: 1 mg, 1.5 ml, 200 mg etc.
    """

    def __init__(
        self,
        min_amount: int | float,
        max_amount: int | float,
        units: Iterable[str],
        allow_floats: bool = True,
        precision: int = 2,
    ):
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.allowed_units = units
        self.allow_floats = allow_floats
        self.precision = precision

        if not allow_floats and (
            isinstance(min_amount, float) or isinstance(max_amount, float)
        ):
            raise ValueError(
                "If floats are not allowed, min_amount and max_amount must be integers"
            )

    def __call__(self, value: str):
        try:
            amount, unit = value.split(" ", maxsplit=1)
            if unit not in self.allowed_units:
                raise ValidationError(
                    f"Unit must be one of {', '.join(self.allowed_units)}"
                )

            amount_number: int | float = float(amount)
            if amount_number.is_integer():
                amount_number = int(amount_number)
            elif not self.allow_floats:
                raise ValidationError("Input amount must be an integer")
            elif len(str(amount_number).split(".")[1]) > self.precision:
                raise ValidationError("Input amount must have at most 4 decimal places")

            if len(amount) != len(str(amount_number)):
                raise ValidationError(
                    f"Input amount must be a valid number without leading{' or trailing ' if self.allow_floats else ' '}zeroes"
                )

            if self.min_amount > amount_number or amount_number > self.max_amount:
                raise ValidationError(
                    f"Input amount must be between {self.min_amount} and {self.max_amount}"
                )
        except ValueError:
            raise ValidationError(
                "Invalid Input, must be in the format: <amount> <unit>"
            )

    def clean(self, value: str):
        if value is None:
            return None
        return value.strip()

    def __eq__(self, __value: object) -> bool:  # pragma: no cover
        if not isinstance(__value, DenominationValidator):
            return False
        return (
            self.min_amount == __value.min_amount
            and self.max_amount == __value.max_amount
            and self.allowed_units == __value.allowed_units
            and self.allow_floats == __value.allow_floats
            and self.precision == __value.precision
        )


dosage_validator = DenominationValidator(
    min_amount=0.0001,
    max_amount=5000,
    units={"mg", "g", "ml", "drop(s)", "ampule(s)", "tsp", "mcg", "unit(s)"},
    allow_floats=True,
    precision=4,
)

custom_image_extension_validator = validators.FileExtensionValidator(
    allowed_extensions=["jpg", "jpeg", "png"]
)
