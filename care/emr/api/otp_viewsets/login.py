import logging
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field, field_validator
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.locks.otp import OTPSendLock, OTPVerifyLock
from care.facility.models.patient import MobileOTP
from care.utils import sms
from care.utils.models.validators import mobile_validator
from care.utils.time_util import care_now
from config.patient_otp_token import PatientToken

logger = logging.getLogger(__name__)


def generate_otp(size):
    return "".join(secrets.choice(string.digits) for _ in range(size))


class BaseOTPType:
    @classmethod
    def render_content(cls, otp: str) -> str:
        raise NotImplementedError

    @classmethod
    def send_window(cls) -> timedelta:
        raise NotImplementedError

    @classmethod
    def max_sends(cls) -> int:
        raise NotImplementedError


class LoginOTP(BaseOTPType):
    @classmethod
    def render_content(cls, otp: str) -> str:
        return settings.OTP_SMS_LOGIN_CONTENT.format(otp=otp)

    @classmethod
    def send_window(cls) -> timedelta:
        return timedelta(minutes=settings.OTP_SEND_WINDOW_MINUTES)

    @classmethod
    def max_sends(cls) -> int:
        return settings.OTP_MAX_SENDS_PER_WINDOW


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


def failure_count(phone_number: str) -> int:
    since = care_now() - timedelta(minutes=settings.OTP_LOCKOUT_MINUTES)
    total = MobileOTP.objects.filter(
        phone_number=phone_number,
        modified_date__gte=since,
        failed_attempts__gt=0,
    ).aggregate(total=Sum("failed_attempts"))["total"]
    return total or 0


def send_otp(phone_number, otp_type: type[BaseOTPType]):
    with OTPSendLock(phone_number):
        if failure_count(phone_number) >= settings.OTP_MAX_FAILURES:
            raise Throttled(detail="Too many failed login attempts. Try again later.")

        sent_otps = MobileOTP.objects.filter(
            created_date__gte=care_now() - otp_type.send_window(),
            phone_number=phone_number,
        )
        if sent_otps.count() >= otp_type.max_sends():
            raise ValidationError({"phone_number": "Max Retries has exceeded"})

        otp_value = (
            generate_otp(settings.OTP_LENGTH) if settings.IS_PRODUCTION else "45612"
        )
        if settings.USE_SMS:
            try:
                content = otp_type.render_content(otp_value)
                sms.send_text_message(
                    content=content,
                    recipients=[phone_number],
                )
            except Exception as e:
                logger.error(e)
                raise ValidationError(
                    {"error": "Error while sending OTP. Contact admin."}
                ) from e
        elif settings.IS_PRODUCTION:
            raise APIException("SMS Backend not configured")

        # disable all other existing otp before creating a new one
        MobileOTP.objects.filter(phone_number=phone_number, is_used=False).update(
            is_used=True
        )
        MobileOTP.objects.create(phone_number=phone_number, otp=otp_value)


class OTPLoginView(EMRBaseViewSet):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=OTPRequestBaseSpec,
    )
    @action(detail=False, methods=["POST"])
    def send(self, request):
        data = OTPRequestBaseSpec(**request.data)
        send_otp(data.phone_number, otp_type=LoginOTP)
        return Response({"otp": "generated"})

    @extend_schema(
        request=OTPLoginSpec,
    )
    @action(detail=False, methods=["POST"])
    def login(self, request):
        data = OTPLoginSpec(**request.data)

        expired = False
        with OTPVerifyLock(data.phone_number):
            if failure_count(data.phone_number) >= settings.OTP_MAX_FAILURES:
                raise Throttled(
                    detail="Too many failed login attempts. Try again later."
                )

            otp_object = (
                MobileOTP.objects.filter(
                    phone_number=data.phone_number,
                    is_used=False,
                    created_date__gte=care_now()
                    - timedelta(minutes=settings.OTP_VALIDITY_MINUTES),
                )
                .order_by("-created_date")
                .first()
            )

            if otp_object:
                if otp_object.otp == data.otp:
                    otp_object.is_used = True
                    otp_object.save(update_fields=["is_used", "modified_date"])
                    token = PatientToken()
                    token["phone_number"] = data.phone_number
                    return Response({"access": str(token)})
                otp_object.failed_attempts += 1
                if otp_object.failed_attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
                    otp_object.is_used = True
                    expired = True
                otp_object.save(
                    update_fields=["failed_attempts", "is_used", "modified_date"]
                )

        if expired:
            raise ValidationError(
                {"otp": "Too many wrong attempts. Please request a new OTP."}
            )
        raise ValidationError({"otp": "Invalid OTP"})
