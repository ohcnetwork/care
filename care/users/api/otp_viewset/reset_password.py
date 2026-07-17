from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from drf_spectacular.utils import extend_schema
from pydantic import Field
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response

from care.emr.api.otp_viewsets.login import (
    BaseOTPType,
    OTPRequestBaseSpec,
    failure_count,
    send_otp,
)
from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.locks.otp import OTPVerifyLock
from care.facility.models.patient import MobileOTP
from care.users.models import User
from care.utils.time_util import care_now


class OTPResetSendSpec(OTPRequestBaseSpec):
    pass


class ResetPasswordOTP(BaseOTPType):
    @classmethod
    def render_content(cls, otp: str) -> str:
        return settings.OTP_SMS_RESET_PASSWORD_CONTENT.format(otp=otp)

    @classmethod
    def send_window(cls) -> timedelta:
        return timedelta(hours=settings.OTP_REPEAT_WINDOW)

    @classmethod
    def max_sends(cls) -> int:
        return settings.OTP_MAX_REPEATS_WINDOW


class OTPResetConfirmSpec(OTPRequestBaseSpec):
    otp: str = Field(min_length=settings.OTP_LENGTH, max_length=settings.OTP_LENGTH)
    password: str = Field(min_length=8)
    username: str | None = None


class OTPResetPasswordView(EMRBaseViewSet):
    authentication_classes = []
    permission_classes = []

    @action(detail=False, methods=["POST"])
    @extend_schema(request=OTPResetSendSpec)
    def send(self, request):
        data = OTPResetSendSpec(**request.data)

        if not User.objects.filter(phone_number=data.phone_number).exists():
            return Response({"otp": "generated"})

        send_otp(data.phone_number, otp_type=ResetPasswordOTP)
        return Response({"otp": "generated"})

    @action(detail=False, methods=["POST"])
    @extend_schema(request=OTPResetConfirmSpec)
    def confirm(self, request):
        data = OTPResetConfirmSpec(**request.data)

        expired = False
        with OTPVerifyLock(data.phone_number):
            if failure_count(data.phone_number) >= settings.OTP_MAX_FAILURES:
                raise Throttled(detail="Too many failed attempts. Try again later.")

            otp_obj = (
                MobileOTP.objects.filter(
                    phone_number=data.phone_number,
                    is_used=False,
                    created_date__gte=care_now()
                    - timedelta(hours=settings.OTP_REPEAT_WINDOW),
                )
                .order_by("-created_date")
                .first()
            )

            if not otp_obj or otp_obj.otp != data.otp:
                if otp_obj:
                    otp_obj.failed_attempts += 1
                    if otp_obj.failed_attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
                        otp_obj.is_used = True
                        expired = True
                    otp_obj.save(
                        update_fields=["failed_attempts", "is_used", "modified_date"]
                    )
                if expired:
                    raise ValidationError(
                        {"otp": "Too many wrong attempts. Please request a new OTP."}
                    )
                raise ValidationError({"otp": "Invalid OTP"})

        users = User.objects.filter(phone_number=data.phone_number)
        user_count = users.count()
        if user_count == 0:
            raise ValidationError({"error": "No user linked to this phone number"})
        if user_count > 1:
            if data.username:
                users = users.filter(username=data.username)
                if not users.exists():
                    raise ValidationError(
                        {
                            "error": "No User with this username linked to this phone number"
                        }
                    )
            else:
                return Response(
                    {"error": "Multiple users linked to this phone number"},
                    status=409,
                )
        user = users.first()
        if user is None:
            raise ValidationError({"otp": "Invalid OTP"})

        validate_password(
            data.password,
            user=user,
            password_validators=get_password_validators(
                settings.AUTH_PASSWORD_VALIDATORS
            ),
        )
        user.set_password(data.password)
        user.save()
        MobileOTP.objects.filter(
            phone_number=data.phone_number,
        ).delete()
        return Response({"message": "Password reset successful"})
