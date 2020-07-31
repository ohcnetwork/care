import random
import string
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models.patient import PatientMobileOTP


def rand_pass(size):

    generate_pass = "".join([random.choice(string.ascii_uppercase + string.digits) for n in range(size)])

    return generate_pass


class PatientMobileOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMobileOTP
        fields = ("phone_number",)

    def create(self, validated_data):

        # Filter to only allow n sms per phone number per 6 hour

        sent_otps = PatientMobileOTP.objects.filter(
            created_date__gte=(localtime(now()) - timedelta(settings.OTP_REPEAT_WINDOW))
        )

        if sent_otps.count() >= settings.OTP_MAX_REPEATS_WINDOW:
            raise ValidationError({"phone_number": "Max Retries has exceeded"})

        otp_obj = super().create(validated_data)
        otp = rand_pass(settings.OTP_LENGTH)

        print(otp)
        # S4W8Q
        otp_obj.otp = otp
        otp_obj.save()

        return otp_obj
