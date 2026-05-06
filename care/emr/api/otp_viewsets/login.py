import logging
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field, field_validator
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.locks.otp import OTPSendLock
from care.facility.models.patient import PatientMobileOTP
from care.utils import sms
from care.utils.models.validators import mobile_validator
from care.utils.sms.utils import get_sms_content
from config.patient_otp_token import PatientToken

logger = logging.getLogger(__name__)


def rand_pass(size):
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

    def failure_count(self, phone_number: str) -> int:
        since = timezone.now() - timedelta(minutes=settings.OTP_LOCKOUT_MINUTES)
        total = PatientMobileOTP.objects.filter(
            phone_number=phone_number,
            modified_date__gte=since,
            failed_attempts__gt=0,
        ).aggregate(total=Sum("failed_attempts"))["total"]
        return total or 0

    @extend_schema(
        request=OTPLoginRequestSpec,
    )
    @action(detail=False, methods=["POST"])
    def send(self, request):
        data = OTPLoginRequestSpec(**request.data)

        if self.failure_count(data.phone_number) >= settings.OTP_MAX_FAILURES:
            raise Throttled(detail="Too many failed login attempts. Try again later.")

        with OTPSendLock(data.phone_number):
            sent_otps = PatientMobileOTP.objects.filter(
                created_date__gte=(
                    timezone.now() - timedelta(minutes=settings.OTP_SEND_WINDOW_MINUTES)
                ),
                phone_number=data.phone_number,
            )
            if sent_otps.count() >= settings.OTP_MAX_SENDS_PER_WINDOW:
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
                    logger.error(e)
                    return Response(
                        {"error": "Error while sending OTP. Contact admin."},
                        status=400,
                    )
            elif settings.IS_PRODUCTION:
                random_otp = rand_pass(settings.OTP_LENGTH)
            else:
                random_otp = "45612"

            # disable all other existing otp before creating a new one
            PatientMobileOTP.objects.filter(
                phone_number=data.phone_number, is_used=False
            ).update(is_used=True)
            PatientMobileOTP.objects.create(
                phone_number=data.phone_number, otp=random_otp
            )
        return Response({"otp": "generated"})

    @extend_schema(
        request=OTPLoginSpec,
    )
    @action(detail=False, methods=["POST"])
    def login(self, request):
        data = OTPLoginSpec(**request.data)

        if self.failure_count(data.phone_number) >= settings.OTP_MAX_FAILURES:
            raise Throttled(detail="Too many failed login attempts. Try again later.")

        expired = False
        with transaction.atomic():
            otp_object = (
                PatientMobileOTP.objects.select_for_update()
                .filter(phone_number=data.phone_number, is_used=False)
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
