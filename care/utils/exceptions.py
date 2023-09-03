from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class CeleryTaskError(Exception):
    pass


class CaptchaRequiredException(AuthenticationFailed):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _("Too Many Requests Provide Captcha")
    default_code = "captchaRequired"
