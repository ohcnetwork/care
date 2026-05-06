import logging
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
from rest_framework.viewsets import GenericViewSet

from care.emr.api.otp_viewsets.login import OTPRequestBaseSpec, OTPType, send_otp
from care.facility.models.patient import MobileOTP
from care.users.models import User
from config.ratelimit import ratelimit

logger = logging.getLogger(__name__)


class OTPResetSendSpec(OTPRequestBaseSpec):
    pass


class OTPResetConfirmSpec(OTPRequestBaseSpec):
    otp: str = Field(min_length=settings.OTP_LENGTH, max_length=settings.OTP_LENGTH)
    password: str = Field(min_length=8)


class OTPResetPasswordView(GenericViewSet):
    authentication_classes = []
    permission_classes = []

    @action(detail=False, methods=["POST"])
    @extend_schema(request=OTPResetSendSpec)
    def send(self, request):
        data = OTPResetSendSpec(**request.data)

        if ratelimit(request, "otp-password-reset", ["ip"]):
            error_message = "Too many requests. Please try again later."
            return Response(
                {"detail": error_message},
                status=429,
            )

        if not User.objects.filter(phone_number=data.phone_number).exists():
            return Response({"otp": "generated"})

        error_response = send_otp(
            data.phone_number,
            purpose=OTPType.reset_password,
        )
        if error_response:
            return error_response
        return Response({"otp": "generated"})

    @action(detail=False, methods=["POST"])
    @extend_schema(request=OTPResetConfirmSpec)
    def confirm(self, request):
        data = OTPResetConfirmSpec(**request.data)
        if ratelimit(request, "otp-password-confirm", ["ip"]):
            error_message = "Too many requests. Please try again later."
            return Response(
                {"detail": error_message},
                status=429,
            )
        user = User.objects.filter(phone_number=data.phone_number).first()
        if not user:
            raise ValidationError({"error": "No User linked to this phone number"})
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
        if not otp_obj or otp_obj.otp != data.otp:
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
