from django.core.exceptions import ValidationError
from django.test import TestCase

from care.utils.models.validators import PhoneNumberValidator


class PhoneNumberValidatorTests(TestCase):
    mobile_validator = PhoneNumberValidator(types=("mobile",))
    indian_mobile_validator = PhoneNumberValidator(types=("indian_mobile",))
    international_mobile_validator = PhoneNumberValidator(
        types=("international_mobile",)
    )
    landline_validator = PhoneNumberValidator(types=("landline",))
    support_validator = PhoneNumberValidator(types=("support",))

    valid_indian_mobile_numbers = [
        "+919876543210",
    ]

    valid_international_mobile_numbers = [
        "+44712345678",
        "+447123456789",
        "+4471234567890",
        "+44712345678901",
        "+447123456789012",
        "+4471234567890123",
        "+44712345678901234",
    ]

    valid_landline_numbers = [
        "+914902626488",
    ]

    valid_support_numbers = [
        "1800123456",
        "18001234567",
        "1860123456",
        "18601234567",
    ]

    invalid_indian_mobile_numbers = [
        *valid_support_numbers,
        *valid_international_mobile_numbers,
        "+915678847123",
        "9876543210",
        "98765432101",
        "987654321a",
        "+9198765432100",
        "+91 9876543210",
        "98765 43210",
        "98765-43210",
    ]

    invalid_international_mobile_numbers = [
        *valid_support_numbers,
        *valid_indian_mobile_numbers,
        "4471234567",
        "447123456789012345",
        "+447123456789012345",
        "+44 7123456789012345",
        "4471234567890123456",
        "+4471234567890123456",
        "+44 71234567890123456",
    ]

    invalid_landline_numbers = [
        *valid_support_numbers,
        "4902626488",
        "02226543210",
        "022 26543210",
        "022-26543210",
    ]

    invalid_support_numbers = [
        *valid_indian_mobile_numbers,
        *valid_international_mobile_numbers,
        *valid_landline_numbers,
        "180012345",
        "180012345678",
        "186012345",
        "186012345678",
    ]

    def test_valid_mobile_numbers(self):
        for number in (
            self.valid_indian_mobile_numbers + self.valid_international_mobile_numbers
        ):
            self.assertIsNone(self.mobile_validator(number), msg=f"Failed for {number}")

    def test_valid_indian_mobile_numbers(self):
        for number in self.valid_indian_mobile_numbers:
            self.assertIsNone(
                self.indian_mobile_validator(number), msg=f"Failed for {number}"
            )

    def test_valid_international_mobile_numbers(self):
        for number in self.valid_international_mobile_numbers:
            self.assertIsNone(
                self.international_mobile_validator(number), msg=f"Failed for {number}"
            )

    def test_valid_landline_numbers(self):
        for number in self.valid_landline_numbers:
            self.assertIsNone(
                self.landline_validator(number), msg=f"Failed for {number}"
            )

    def test_valid_support_numbers(self):
        for number in self.valid_support_numbers:
            self.assertIsNone(
                self.support_validator(number), msg=f"Failed for {number}"
            )

    def test_invalid_indian_mobile_numbers(self):
        for number in self.invalid_indian_mobile_numbers:
            with self.assertRaises(ValidationError, msg=f"Failed for {number}"):
                self.indian_mobile_validator(number)

    def test_invalid_international_mobile_numbers(self):
        for number in self.invalid_international_mobile_numbers:
            with self.assertRaises(ValidationError, msg=f"Failed for {number}"):
                self.international_mobile_validator(number)

    def test_invalid_landline_numbers(self):
        for number in self.invalid_landline_numbers:
            with self.assertRaises(ValidationError, msg=f"Failed for {number}"):
                self.landline_validator(number)

    def test_invalid_support_numbers(self):
        for number in self.invalid_support_numbers:
            with self.assertRaises(ValidationError, msg=f"Failed for {number}"):
                self.support_validator(number)
