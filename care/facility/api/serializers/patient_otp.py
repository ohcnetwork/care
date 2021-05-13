import random
import string
from datetime import timedelta

import boto3
from django.conf import settings
from django.utils.timezone import localtime, now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.models.patient import PatientMobileOTP

from care.utils.sms.sendSMS import sendSMS


def rand_pass(size):

    generate_pass = "".join([random.choice(string.ascii_uppercase + string.digits) for n in range(size)])

    return generate_pass


def send_sms(otp, phone_number):

    if settings.USE_SMS:
        sendSMS(
            phone_number,
            "CoronaSafe Network Patient Management System Login, OTP is {} . Please do not share this Confidential Login Token with anyone else".format(
                otp
            ),
        )
    else:
        print(otp, phone_number)


class PatientMobileOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMobileOTP
        fields = ("phone_number",)

    def create(self, validated_data):

        # Filter to only allow n sms per phone number per 6 hour

        sent_otps = PatientMobileOTP.objects.filter(
            created_date__gte=(localtime(now()) - timedelta(settings.OTP_REPEAT_WINDOW)),
            is_used=False,
            phone_number=validated_data["phone_number"],
        )

        if sent_otps.count() >= settings.OTP_MAX_REPEATS_WINDOW:
            raise ValidationError({"phone_number": "Max Retries has exceeded"})

        otp_obj = super().create(validated_data)
        otp = rand_pass(settings.OTP_LENGTH)

        send_sms(otp, otp_obj.phone_number)

        otp_obj.otp = otp
        otp_obj.save()

        return otp_obj
