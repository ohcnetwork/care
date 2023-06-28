from django.core.exceptions import ValidationError
from django.test import TestCase

from care.users.models import phone_number_regex


class PhoneNumberValidatorTests(TestCase):
    def test_valid_phone_number(self):
        self.assertIsNone(phone_number_regex("+919876543210"))
        self.assertIsNone(phone_number_regex("9876543210"))
        self.assertIsNone(phone_number_regex("02228820000"))

    def test_invalid_phone_number(self):
        with self.assertRaises(ValidationError):
            phone_number_regex("987654321")
        with self.assertRaises(ValidationError):
            phone_number_regex("98765432101")
        with self.assertRaises(ValidationError):
            phone_number_regex("987654321a")
        with self.assertRaises(ValidationError):
            phone_number_regex("+9198765432100")
        with self.assertRaises(ValidationError):
            phone_number_regex("+91 9876543210")
        with self.assertRaises(ValidationError):
            phone_number_regex("98765 43210")
        with self.assertRaises(ValidationError):
            phone_number_regex("98765-43210")
        with self.assertRaises(ValidationError):
            phone_number_regex("022 26543210")
