from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import get_error_detail
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(detail={"detail": get_error_detail(exc)[0]})

    return drf_exception_handler(exc, context)
