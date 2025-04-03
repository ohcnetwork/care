import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field, field_validator
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.facility.models.patient import PatientMobileOTP
from care.utils import sms
from care.utils.models.validators import mobile_validator
from care.utils.sms.utils import get_sms_content
from config.patient_otp_token import PatientToken


def rand_pass(size):
    if not settings.USE_SMS:
        return "45612"

    return "".join(secrets.choice(string.digits) for _ in range(size))


class OTPLoginRequestSpec(BaseModel):
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


class OTPLoginSpec(OTPLoginRequestSpec):
    otp: str = Field(min_length=settings.OTP_LENGTH, max_length=settings.OTP_LENGTH)


class OTPLoginView(EMRBaseViewSet):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=OTPLoginRequestSpec,
    )
    @action(detail=False, methods=["POST"])
    def send(self, request):
        data = OTPLoginRequestSpec(**request.data)
        sent_otps = PatientMobileOTP.objects.filter(
            created_date__gte=(timezone.now() - timedelta(settings.OTP_REPEAT_WINDOW)),
            is_used=False,
            phone_number=data.phone_number,
        )
        if sent_otps.count() >= settings.OTP_MAX_REPEATS_WINDOW:
            raise ValidationError({"phone_number": "Max Retries has exceeded"})
        random_otp = ""
        if settings.USE_SMS:
            random_otp = rand_pass(settings.OTP_LENGTH)
            try:
                content = get_sms_content(
                    settings.OTP_SMS_TEMPLATE_PATH, {"random_otp": random_otp}
                )
                sms.send_text_message(
                    content=content,
                    recipients=[data.phone_number],
                )
            except Exception as e:
                import logging

                logging.error(e)
                return Response(
                    {"error": "Error while sending OTP. Contact admin."}, status=400
                )
        else:
            random_otp = "45612"

        otp_obj = PatientMobileOTP(phone_number=data.phone_number, otp=random_otp)
        otp_obj.save()
        return Response({"otp": "generated"})

    @extend_schema(
        request=OTPLoginSpec,
    )
    @action(detail=False, methods=["POST"])
    def login(self, request):
        data = OTPLoginSpec(**request.data)
        otp_object = PatientMobileOTP.objects.filter(
            phone_number=data.phone_number, otp=data.otp, is_used=False
        ).first()
        if not otp_object:
            raise ValidationError({"otp": "Invalid OTP"})

        otp_object.is_used = True
        otp_object.save()

        token = PatientToken()
        token["phone_number"] = data.phone_number

        return Response({"access": str(token)})
