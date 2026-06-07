from datetime import timedelta

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models.patient import MobileOTP
from care.utils.time_util import care_now


@override_settings(
    USE_SMS=False,
    IS_PRODUCTION=False,
    OTP_MAX_VERIFY_ATTEMPTS=3,
    OTP_MAX_FAILURES=5,
    OTP_LOCKOUT_MINUTES=30,
    OTP_SEND_WINDOW_MINUTES=60,
    OTP_MAX_SENDS_PER_WINDOW=10,
    OTP_VALIDITY_MINUTES=10,
)
class OTPLoginFlowTests(APITestCase):
    SEND_URL = "/api/v1/otp/send/"
    LOGIN_URL = "/api/v1/otp/login/"
    PHONE = "+919999999999"
    DEV_OTP = "45612"  # value hard-coded in send() for non-prod, non-SMS path
    WRONG_OTP = "00000"

    def _send(self, phone=None):
        return self.client.post(
            self.SEND_URL,
            {"phone_number": phone or self.PHONE},
            format="json",
        )

    def _login(self, otp, phone=None):
        return self.client.post(
            self.LOGIN_URL,
            {"phone_number": phone or self.PHONE, "otp": otp},
            format="json",
        )

    # ------------------------------------------------------------------ happy path

    def test_send_creates_otp_row(self):
        resp = self._send()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(MobileOTP.objects.filter(phone_number=self.PHONE).count(), 1)

    def test_login_with_correct_otp_returns_token(self):
        self._send()
        resp = self._login(self.DEV_OTP)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertTrue(MobileOTP.objects.get(phone_number=self.PHONE).is_used)

    def test_used_otp_cannot_be_reused(self):
        self._send()
        self.assertEqual(self._login(self.DEV_OTP).status_code, 200)
        # second login with the same code must fail; row is is_used=True so no
        # latest unused OTP exists -> "Invalid OTP", failure NOT counted
        resp = self._login(self.DEV_OTP)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ per-OTP cap

    def test_third_wrong_attempt_invalidates_otp(self):
        self._send()
        self.assertEqual(self._login(self.WRONG_OTP).status_code, 400)
        self.assertEqual(self._login(self.WRONG_OTP).status_code, 400)

        resp = self._login(self.WRONG_OTP)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("request a new OTP", str(resp.data))

        otp_row = MobileOTP.objects.get(phone_number=self.PHONE)
        self.assertTrue(otp_row.is_used)
        self.assertEqual(otp_row.failed_attempts, 3)

        # even the correct code now fails — OTP is dead
        resp = self._login(self.DEV_OTP)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("request a new OTP", str(resp.data))

    def test_correct_otp_works_after_partial_failures(self):
        self._send()
        self._login(self.WRONG_OTP)
        self._login(self.WRONG_OTP)
        self.assertEqual(self._login(self.DEV_OTP).status_code, 200)

    def test_new_otp_works_after_previous_was_killed(self):
        self._send()
        for _ in range(3):
            self._login(self.WRONG_OTP)
        # OTP #1 killed, but daily failure count = 3 < 5 → can still request
        self.assertEqual(self._send().status_code, 200)
        self.assertEqual(self._login(self.DEV_OTP).status_code, 200)

    @override_settings(OTP_MAX_VERIFY_ATTEMPTS=1)
    def test_setting_override_kills_otp_on_first_wrong_attempt(self):
        self._send()
        resp = self._login(self.WRONG_OTP)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("request a new OTP", str(resp.data))

    # ------------------------------------------------------------------ phone lockout

    def test_phone_locked_out_after_max_failures_blocks_login(self):
        # 5 failures across two OTPs (3 + 2)
        self._send()
        for _ in range(3):
            self._login(self.WRONG_OTP)
        self._send()
        for _ in range(2):
            self._login(self.WRONG_OTP)

        # 6th attempt -> lockout
        resp = self._login(self.WRONG_OTP)
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_phone_locked_out_blocks_send_too(self):
        self._send()
        for _ in range(3):
            self._login(self.WRONG_OTP)
        self._send()
        for _ in range(2):
            self._login(self.WRONG_OTP)

        resp = self._send()
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_lockout_does_not_affect_other_phone_numbers(self):
        # lock out PHONE
        self._send()
        for _ in range(3):
            self._login(self.WRONG_OTP)
        self._send()
        for _ in range(2):
            self._login(self.WRONG_OTP)

        other = "+918888888888"
        self.assertEqual(self._send(phone=other).status_code, 200)
        self.assertEqual(self._login(self.DEV_OTP, phone=other).status_code, 200)

    def test_lockout_window_slides_over_time(self):
        self._send()
        for _ in range(3):
            self._login(self.WRONG_OTP)
        self._send()
        for _ in range(2):
            self._login(self.WRONG_OTP)
        self.assertEqual(self._send().status_code, 429)

        # age all existing failures past the lockout window
        old = care_now() - timedelta(minutes=31)
        MobileOTP.objects.filter(phone_number=self.PHONE).update(modified_date=old)

        # window has slid; the phone is unlocked again
        self.assertEqual(self._send().status_code, 200)

    # ------------------------------------------------------------------ send rate limit

    def test_send_rate_limit_enforced_within_window(self):
        for _ in range(10):
            self.assertEqual(self._send().status_code, 200)
        resp = self._send()
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_rate_limit_window_excludes_old_otps(self):
        for _ in range(10):
            self._send()
        # age them past the send window
        old = care_now() - timedelta(minutes=61)
        MobileOTP.objects.filter(phone_number=self.PHONE).update(created_date=old)
        self.assertEqual(self._send().status_code, 200)

    def test_send_rate_limit_counts_used_otps(self):
        """Send cap counts every OTP issued in the window, not just unused ones —
        otherwise a client that consumes each OTP could bypass the cap entirely."""
        for _ in range(10):
            self.assertEqual(self._send().status_code, 200)
            # consume the OTP so only used rows remain
            self._login(self.DEV_OTP)
        resp = self._send()
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ multi-OTP behavior

    def test_only_latest_unused_otp_is_validated(self):
        # First OTP issued
        self._send()
        first_id = MobileOTP.objects.latest("created_date").id

        # Issuing a new OTP must invalidate the older one (no two unused OTPs alive at once)
        self._send()
        first_row = MobileOTP.objects.get(id=first_id)
        self.assertTrue(first_row.is_used)

        # Login uses only the newest unused row
        resp = self._login(self.DEV_OTP)
        self.assertEqual(resp.status_code, 200)

    def test_old_otp_cannot_login_after_new_one_issued(self):
        """Even if an attacker knows an old OTP code, it must not work after a re-send."""
        self._send()
        # User re-requests; old row becomes is_used=True
        self._send()
        # Consume the new OTP
        self.assertEqual(self._login(self.DEV_OTP).status_code, 200)
        # No unused OTP rows for this phone now
        self.assertFalse(
            MobileOTP.objects.filter(phone_number=self.PHONE, is_used=False).exists()
        )
        # Replaying the (same-value) old code must fail — no unused row to match against
        resp = self._login(self.DEV_OTP)
        self.assertEqual(resp.status_code, 400)

    def test_failure_bumps_only_latest_otp_row(self):
        self._send()
        first_id = MobileOTP.objects.latest("created_date").id
        self._send()
        second_id = MobileOTP.objects.latest("created_date").id
        self.assertNotEqual(first_id, second_id)

        self._login(self.WRONG_OTP)

        self.assertEqual(MobileOTP.objects.get(id=first_id).failed_attempts, 0)
        self.assertEqual(MobileOTP.objects.get(id=second_id).failed_attempts, 1)

    # ------------------------------------------------------------------ no-OTP edge

    def test_login_with_no_active_otp_returns_400_without_bumping(self):
        resp = self._login(self.WRONG_OTP)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(MobileOTP.objects.count(), 0)

    # ------------------------------------------------------------------ otp validity

    def test_expired_otp_cannot_login(self):
        self._send()
        # age the OTP past its validity window
        old = care_now() - timedelta(minutes=11)
        MobileOTP.objects.filter(phone_number=self.PHONE).update(created_date=old)
        resp = self._login(self.DEV_OTP)
        self.assertEqual(resp.status_code, 400)
        # row remains unused since it was never picked up by the verify query
        self.assertFalse(MobileOTP.objects.get(phone_number=self.PHONE).is_used)

    def test_otp_within_validity_window_works(self):
        self._send()
        # age the OTP to just inside the validity window
        recent = care_now() - timedelta(minutes=9)
        MobileOTP.objects.filter(phone_number=self.PHONE).update(created_date=recent)
        resp = self._login(self.DEV_OTP)
        self.assertEqual(resp.status_code, 200)
