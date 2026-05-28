from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pydantic import Field
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.otp_viewsets.login import BaseOTPType, OTPRequestBaseSpec, send_otp
from care.emr.api.viewsets.base import EMRBaseViewSet
from care.facility.models.patient import MobileOTP
from care.users.models import User


class OTPResetSendSpec(OTPRequestBaseSpec):
    pass


class ResetPasswordOTP(BaseOTPType):
    @classmethod
    def render_content(cls, otp: str) -> str:
        return settings.OTP_SMS_RESET_PASSWORD_CONTENT.format(otp=otp)


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

        try:
            send_otp(data.phone_number, otp_type=ResetPasswordOTP)
        except ValueError as e:
            raise ValidationError({"phone_number": "Unable to send OTP"}) from e
        except Exception:
            return Response({"error": "Unable to send OTP"}, status=400)
        return Response({"otp": "generated"})

    @action(detail=False, methods=["POST"])
    @extend_schema(request=OTPResetConfirmSpec)
    def confirm(self, request):
        data = OTPResetConfirmSpec(**request.data)
        otp_obj = (
            MobileOTP.objects.filter(
                phone_number=data.phone_number,
                is_used=False,
                created_date__gte=(
                    timezone.now() - timedelta(hours=settings.OTP_REPEAT_WINDOW)
                ),
            )
            .order_by("-created_date")
            .first()
        )
        users = User.objects.filter(phone_number=data.phone_number)
        user_count = users.count()
        if not otp_obj or otp_obj.otp != data.otp:
            raise ValidationError({"otp": "Invalid OTP"})

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
