import logging
import secrets
import string
from datetime import timedelta
from enum import Enum

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field, field_validator
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.facility.models.patient import MobileOTP
from care.utils import sms
from care.utils.models.validators import mobile_validator
from config.patient_otp_token import PatientToken

logger = logging.getLogger(__name__)


class OTPType(str, Enum):
    login = "login"
    reset_password = "reset_password"


def rand_pass(size):
    return "".join(secrets.choice(string.digits) for _ in range(size))


def send_otp(phone_number, purpose):
    sent_otps = MobileOTP.objects.filter(
        created_date__gte=(timezone.now() - timedelta(settings.OTP_REPEAT_WINDOW)),
        is_used=False,
        phone_number=phone_number,
    )
    if sent_otps.count() >= settings.OTP_MAX_REPEATS_WINDOW:
        raise ValidationError({"phone_number": "Max Retries has exceeded"})

    random_otp = ""
    if settings.USE_SMS:
        random_otp = rand_pass(settings.OTP_LENGTH)
        try:
            if purpose == OTPType.login:
                content = settings.OTP_SMS_CONTENT.format(otp=random_otp)
            elif purpose == OTPType.reset_password:
                content = settings.OTP_SMS_RESET_PASSWORD_CONTENT.format(otp=random_otp)

            sms.send_text_message(
                content=content,
                recipients=[phone_number],
            )
        except Exception as e:
            logger.error(e)
            return Response(
                {"error": "Error while sending OTP. Contact admin."}, status=400
            )
    elif settings.IS_PRODUCTION:
        random_otp = rand_pass(settings.OTP_LENGTH)
    else:
        random_otp = "45612"

    MobileOTP.objects.create(phone_number=phone_number, otp=random_otp)
    return None


class OTPRequestBaseSpec(BaseModel):
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


class OTPLoginSpec(OTPRequestBaseSpec):
    otp: str = Field(min_length=settings.OTP_LENGTH, max_length=settings.OTP_LENGTH)


class OTPLoginView(EMRBaseViewSet):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=OTPRequestBaseSpec,
    )
    @action(detail=False, methods=["POST"])
    def send(self, request):
        data = OTPRequestBaseSpec(**request.data)
        error_response = send_otp(data.phone_number, purpose=OTPType.login)
        if error_response:
            return error_response
        return Response({"otp": "generated"})

    @extend_schema(
        request=OTPLoginSpec,
    )
    @action(detail=False, methods=["POST"])
    def login(self, request):
        data = OTPLoginSpec(**request.data)
        otp_object = MobileOTP.objects.filter(
            phone_number=data.phone_number, otp=data.otp, is_used=False
        ).first()
        if not otp_object:
            raise ValidationError({"otp": "Invalid OTP"})

        otp_object.is_used = True
        otp_object.save()

        token = PatientToken()
        token["phone_number"] = data.phone_number

        return Response({"access": str(token)})
