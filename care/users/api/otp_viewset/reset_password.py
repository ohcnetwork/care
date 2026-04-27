import logging
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field, field_validator
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from care.users.models import User, UserMobileOTP
from care.utils import sms
from care.utils.models.validators import mobile_validator
from care.utils.sms.utils import get_sms_content

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


class OTPResetSendView(GenericAPIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(request=OTPResetSendSpec)
    def post(self, request):
        data = OTPResetSendSpec(**request.data)

        sent_otps = UserMobileOTP.objects.filter(
            created_date__gte=(
                timezone.now() - timedelta(hours=settings.OTP_REPEAT_WINDOW)
            ),
            is_used=False,
            phone_number=data.phone_number,
        )
        if sent_otps.count() >= settings.OTP_MAX_REPEATS_WINDOW:
            raise ValidationError(
                {"phone_number": "Max OTP requests exceeded. Try again later."}
            )
        if not User.objects.filter(phone_number=data.phone_number).exists():
            return Response({"otp": "generated"})

        random_otp = rand_pass(settings.OTP_LENGTH)
        logger.info(random_otp)
        try:
            content = get_sms_content(
                settings.OTP_SMS_RESET_PASSWORD_TEMPLATE_PATH,
                {"random_otp": random_otp},
            )
            sms.send_text_message(
                content=content,
                recipients=[data.phone_number],
            )
        except Exception as e:
            logger.error(e)
            return Response(
                {"error": "Error while sending OTP. Contact admin."}, status=400
            )

        UserMobileOTP.objects.create(phone_number=data.phone_number, otp=random_otp)
        return Response({"otp": "generated"})


class OTPResetConfirmView(GenericAPIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(request=OTPResetConfirmSpec)
    def post(self, request):
        data = OTPResetConfirmSpec(**request.data)
        user = User.objects.filter(phone_number=data.phone_number).first()
        if not user:
            raise ValidationError({"phone_number": "No account found"})
        otp_obj = (
            UserMobileOTP.objects.filter(
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

        UserMobileOTP.objects.filter(
            phone_number=data.phone_number,
        ).delete()

        user.set_password(data.password)
        user.save()
        return Response({"message": "Password reset successful"})
