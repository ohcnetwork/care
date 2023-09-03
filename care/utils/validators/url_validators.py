from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class MiddlewareDomainAddressValidator(RegexValidator):
    regex = r"^(?!https?:\/\/)[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)*\.[a-zA-Z]{2,}$"
    code = "invalid_domain_name"
    message = _(
        "The domain name is invalid. "
        "It should not start with scheme and "
        "should not end with a trailing slash.",
    )
