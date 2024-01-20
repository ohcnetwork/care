from celery import current_app
from django.core.exceptions import ValidationError as DjangoValidationError
from redis.exceptions import ResponseError as RedisResponseError
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import get_error_detail
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(detail={"detail": get_error_detail(exc)[0]})

    elif isinstance(exc, RedisResponseError):
        current_app.send_task("care.facility.tasks.redis_index.load_redis_index")
        exc = APIException(
            detail={"detail": "Something went wrong, please try after a few seconds."}
        )

    return drf_exception_handler(exc, context)
