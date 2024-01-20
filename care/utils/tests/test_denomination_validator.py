from django.core.exceptions import ValidationError
from django.test import TestCase

from care.utils.models.validators import DenominationValidator


class DenominationValidatorTestCase(TestCase):
    def test_init_with_invalid_range_values(self):
        with self.assertRaises(ValueError):
            DenominationValidator(
                min_amount=100.30, max_amount=1, allow_floats=False, units=["mg"]
            )

    def test_validation_error_on_floats(self):
        validator = DenominationValidator(
            min_amount=1, max_amount=100, allow_floats=False, units=["mg"]
        )
        with self.assertRaises(ValidationError):
            validator("1.1 mg")
