import logging
import secrets
import string

from django.conf import settings
from pydantic import BaseModel, Field, field_validator

from care.utils.models.validators import mobile_validator

logger = logging.getLogger(__name__)


def rand_pass(size):
    if not settings.USE_SMS:
        return "45612"

    return "".join(secrets.choice(string.digits) for _ in range(size))


class OTPBaseSpec(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value):
        try:
            mobile_validator(value)
        except Exception as e:
            msg = "Invalid phone number"
            raise ValueError(msg) from e
        return value


class OTPResetSendSpec(OTPBaseSpec):
    pass


class OTPResetConfirmSpec(OTPBaseSpec):
    otp: str = Field(min_length=settings.OTP_LENGTH, max_length=settings.OTP_LENGTH)
    password: str = Field(min_length=4)
