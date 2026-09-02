from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from care.facility.models.patient import MobileOTP
from care.utils.tests.base import CareAPITestBase


@override_settings(
    OTP_REPEAT_WINDOW=60,
    OTP_MAX_REPEATS_WINDOW=3,
    OTP_LENGTH=6,
    USE_SMS=False,
    IS_PRODUCTION=False,
)
class OTPResetPasswordAPITestCase(CareAPITestBase):
    def setUp(self):
        self.user = self.create_user(
            username="testuser", phone_number="+919876543210", password="OldPass123!"
        )
        self.phone_number = "+919876543210"
        self.password = "OldPass123!"
        self.new_password = "NewPass123!"
        self.send_otp_url = reverse("otp-password-reset-send")
        self.confirm_otp_url = reverse("otp-password-reset-confirm")
        self.otp = "45612"  # As per settings in override, OTP will be this value

    def _send(self, phone_number=None):
        return self.client.post(
            self.send_otp_url,
            {"phone_number": phone_number or self.phone_number},
            format="json",
        )

    def _confirm(self, otp, phone_number=None, username=None, password=None):
        payload = {
            "phone_number": phone_number or self.phone_number,
            "otp": otp,
            "password": password or self.new_password,
        }
        if username is not None:
            payload["username"] = username
        return self.client.post(
            self.confirm_otp_url,
            payload,
            format="json",
        )

    def test_send_otp_request_by_exisiting_user(self):
        """
        When a valid phone number is provided, OTP should be generated and saved in the database,
        regardless of whether the phone number is linked to a user or not,
        to avoid leaking information about registered phone numbers."""

        response = self._send()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["otp"], "generated")
        self.assertTrue(
            MobileOTP.objects.filter(phone_number=self.phone_number).exists()
        )

    def test_send_otp_request_by_non_exisiting_user(self):
        """
        When a valid phone number is provided, OTP should be generated and saved in the database,
        regardless of whether the phone number is linked to a user or not,
        to avoid leaking information about registered phone numbers
        """
        response = self._send(phone_number="+919876543211")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["otp"], "generated")
        self.assertFalse(
            MobileOTP.objects.filter(phone_number="+919876543211").exists()
        )

    def test_send_opt_request_exceeding_limit(self):
        """
        When OTP request is sent more than allowed limit within the repeat window,
        it should return an error."""
        for _ in range(settings.OTP_MAX_REPEATS_WINDOW):
            self._send()
        response = self._send()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Max Retries has exceeded",
            response.data["errors"][0]["msg"]["phone_number"],
        )

    def test_confirm_otp_with_valid_otp(self):
        """
        When OTP confirmation is done with valid OTP,
        password should be reset successfully."""
        self._send()
        response = self._confirm(otp=self.otp)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_confirm_otp_with_invalid_otp(self):
        """
        When OTP confirmation is done with an invalid OTP,
        it should return an error."""
        self._send()
        response = self._confirm(otp="00000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data["errors"][0]["msg"]["otp"]), "Invalid OTP")

    def test_confirm_otp_with_invalid_phone_number(self):
        """
        if the phone number is invalid, OTP confirmation should fail with invalid OTP error,
        not with invalid phone number error, to avoid leaking information about registered phone numbers.
        """
        self._send(phone_number="+919876543211")
        response = self._confirm(otp=self.otp, phone_number="+919876543211")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data["errors"][0]["msg"]["otp"]), "Invalid OTP")

    def test_confirm_otp_with_multiple_users_linked_to_phone_number_and_no_username(
        self,
    ):
        """
        If multiple users are linked to the same phone number, OTP confirmation should fail with an error indicating multiple users,
        unless a valid username is also provided which is linked to the phone number.
        """
        self.create_user(
            username="testuser2",
            phone_number=self.phone_number,
            password="AnotherPass123!",
        )
        self._send()
        response = self._confirm(otp=self.otp)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn(
            "Multiple users linked to this phone number", response.data["error"]
        )

    def test_confirm_otp_with_multiple_users_linked_to_phone_number_and_with_username(
        self,
    ):
        """
        If multiple users are linked to the same phone number, and a valid username is provided, OTP confirmation should succeed.
        """
        self.create_user(
            username="testuser2",
            phone_number=self.phone_number,
            password="AnotherPass123!",
        )
        self._send()
        response = self._confirm(otp=self.otp, username="testuser")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_confirm_otp_with_multiple_users_linked_to_phone_number_and_with_invalid_username(
        self,
    ):
        """
        If multiple users are linked to the same phone number, and an invalid username is provided,
        OTP confirmation should fail with an error indicating no user with this username linked to this phone number.
        """
        self.create_user(
            username="testuser2",
            phone_number=self.phone_number,
            password="AnotherPass123!",
        )
        self._send()
        response = self._confirm(otp=self.otp, username="invalidusername")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "No User with this username linked to this phone number",
            response.data["errors"][0]["msg"]["error"],
        )

    @override_settings(OTP_MAX_VERIFY_ATTEMPTS=2)
    def test_confirm_otp_attempts_are_capped(self):
        """
        Reset confirm shares login's brute-force protection: after
        OTP_MAX_VERIFY_ATTEMPTS wrong guesses the OTP is burned and even the
        correct OTP is rejected afterwards.
        """
        self._send()
        first = self._confirm(otp="00000")
        self.assertEqual(first.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(first.data["errors"][0]["msg"]["otp"]), "Invalid OTP")

        capped = self._confirm(otp="00001")
        self.assertEqual(capped.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Too many wrong attempts", str(capped.data["errors"][0]["msg"]["otp"])
        )

        # OTP is now burned, so the correct value no longer works.
        correct = self._confirm(otp=self.otp)
        self.assertEqual(correct.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(self.new_password))

    def test_confirm_otp_survives_multiple_user_conflict_for_retry(self):
        """
        A 409 for multiple users must not consume the OTP: the same OTP can be
        retried with a username.
        """
        self.create_user(
            username="testuser2",
            phone_number=self.phone_number,
            password="AnotherPass123!",
        )
        self._send()
        conflict = self._confirm(otp=self.otp)
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT)

        retry = self._confirm(otp=self.otp, username="testuser")
        self.assertEqual(retry.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_confirm_otp_with_no_user_linked_to_phone_number(self):
        """
        If a valid OTP exists for a phone number but no user account is
        linked to that number (e.g. the account was deleted after the OTP
        was generated), confirm should return 400 with a validation error
        instead of crashing with AttributeError on user.set_password().
        """
        phone_number = "+919876543211"
        MobileOTP.objects.create(phone_number=phone_number, otp=self.otp)
        response = self._confirm(otp=self.otp, phone_number=phone_number)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["errors"][0]["msg"]["error"],
            "No user linked to this phone number",
        )
