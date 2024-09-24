import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.models.patient import PatientMobileOTP
from care.utils.sms.send_sms import send_sms


def rand_pass(size):
    if not settings.USE_SMS:
        return "45612"

    return "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(size)
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
        otp = rand_pass(settings.OTP_LENGTH)

        if settings.USE_SMS:
            send_sms(
                otp_obj.phone_number,
                (
                    f"Open Healthcare Network Patient Management System Login, OTP is {otp} . "
                    "Please do not share this Confidential Login Token with anyone else"
                ),
            )
        elif settings.DEBUG:
            print(otp, otp_obj.phone_number)  # noqa: T201

        otp_obj.otp = otp
        otp_obj.save()

        return otp_obj
