from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase


@override_settings(
    OTP_REPEAT_WINDOW=60,
    OTP_MAX_REPEATS_WINDOW=3,
    OTP_LENGTH=6,
    USE_SMS=False,
    IS_PRODUCTION=False,
)
class OTPResetPasswordAPITestCase(APITestCase):
    def setUp(self):
        self.phone_number = "1234567890"
        self.send_otp_url = reverse("otp-reset-password-send")
        self.confirm_otp_url = reverse("otp-reset-password-confirm")

    def _send(self, phone_number=None):
        return self.client.post(
            self.send_otp_url, {"phone_number": phone_number or self.phone_number}
        )

    def _confirm(self, otp, phone_number=None, username=None):
        return self.client.post(
            self.confirm_otp_url,
            {
                "phone_number": phone_number or self.phone_number,
                "otp": otp,
                "username": username,
            },
        )
