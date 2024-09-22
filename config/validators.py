import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class NumberValidator:
    def validate(self, password, user=None):
        if not re.findall(r"\d", password):
            raise ValidationError(
                _("The password must contain at least 1 digit, 0-9."),
                code="password_no_number",
            )

    def get_help_text(self):
        return _("Your password must contain at least 1 digit, 0-9.")


class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.findall("[A-Z]", password):
            raise ValidationError(
                _("The password must contain at least 1 uppercase letter, A-Z."),
                code="password_no_upper",
            )

    def get_help_text(self):
        return _("Your password must contain at least 1 uppercase letter, A-Z.")


class LowercaseValidator:
    def validate(self, password, user=None):
        if not re.findall("[a-z]", password):
            raise ValidationError(
                _("The password must contain at least 1 lowercase letter, a-z."),
                code="password_no_lower",
            )

    def get_help_text(self):
        return _("Your password must contain at least 1 lowercase letter, a-z.")


class SymbolValidator:
    def validate(self, password, user=None):
        if not re.findall(r"[()[\]{}|\\`~!@#$%^&*_\-+=;:'\",<>./?]", password):
            raise ValidationError(
                _(
                    "The password must contain at least 1 symbol: "
                    + r"()[]{}|\`~!@#$%^&*_-+=;:'\",<>./?"
                ),
                code="password_no_symbol",
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least 1 symbol: "
            + r"()[]{}|\`~!@#$%^&*_-+=;:'\",<>./?"
        )


class MiddlewareDomainAddressValidator(RegexValidator):
    regex = r"^(?!https?:\/\/)[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)*\.[a-zA-Z]{2,}$"
    code = "invalid_domain_name"
    message = _(
        "The domain name is invalid. "
        "It should not start with scheme and "
        "should not end with a trailing slash."
    )
