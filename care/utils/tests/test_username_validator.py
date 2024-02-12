from django.core.exceptions import ValidationError
from django.test import TestCase

from care.utils.models.validators import UsernameValidator


class UsernameValidatorTests(TestCase):
    username_validator = UsernameValidator()

    valid_usernames = [
        "user",
        "user123",
        "user_123",
        "user_123-456",
        "useruseruseruser",
        "11useruseruser11",
    ]

    invalid_characters = ["user@123", "user#123", "user?123", "user!123"]

    consecutive_characters = ["user__123", "user--123", "user..123", "user__" "..user"]

    invalid_case = ["User", "USER", "uSeR"]

    invalid_length = ["usr", "user12345678901234567890", "useruseruseruseru"]

    def test_valid_usernames(self):
        for username in self.valid_usernames:
            self.assertIsNone(self.username_validator(username))

    def test_invalid_characters(self):
        for username in self.invalid_characters:
            with self.assertRaises(ValidationError):
                self.username_validator(username)

    def test_consecutive_characters(self):
        for username in self.consecutive_characters:
            with self.assertRaises(ValidationError):
                self.username_validator(username)

    def test_invalid_case(self):
        for username in self.invalid_case:
            with self.assertRaises(ValidationError):
                self.username_validator(username)

    def test_invalid_length(self):
        for username in self.invalid_length:
            with self.assertRaises(ValidationError):
                self.username_validator(username)
