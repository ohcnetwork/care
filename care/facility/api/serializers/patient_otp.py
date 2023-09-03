import secrets
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.models.patient import PatientMobileOTP
from care.utils import sms


def rand_pass(size: int) -> str:
    return secrets.token_urlsafe(size)


def send_sms(otp, phone_number):
    sms.send(
        phone_number,
        (
            f"Open Healthcare Network Patient Management System Login, OTP is {otp} . "
            "Please do not share this Confidential Login Token with anyone else"
        ),
    )


class PatientMobileOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMobileOTP
        fields = ("phone_number",)

    def create(self, validated_data):
        # Filter to only allow n sms per phone number per 6 hour

        sent_otps = PatientMobileOTP.objects.filter(
            created_date__gte=(
                localtime(now()) - timedelta(settings.OTP_REPEAT_WINDOW)
            ),
            is_used=False,
            phone_number=validated_data["phone_number"],
        )

        if sent_otps.count() >= settings.OTP_MAX_REPEATS_WINDOW:
            raise ValidationError({"phone_number": "Max Retries has exceeded"})

        otp_obj = super().create(validated_data)

        if settings.USE_SMS:
            otp = rand_pass(settings.OTP_LENGTH)
            send_sms(otp, otp_obj.phone_number)
        else:
            otp = "45612"

        otp_obj.otp = otp
        otp_obj.save()

        return otp_obj
