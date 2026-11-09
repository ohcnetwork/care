import uuid
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from pyotp import TOTP
from rest_framework import status
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from care.emr.utils.reset_password import generate_password_reset_token
from care.facility.models.patient import MobileOTP
from care.users.models import User
from care.utils.tests.base import CareAPITestBase


@override_settings(USE_SMS=False, IS_PRODUCTION=False)
class PasswordTokenRevocationTests(CareAPITestBase):
    password = "OldSecret173!"
    new_password = "NewSecret284!"

    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = self.create_user_with_password(
            self.password,
            username="revocation_user",
            email="revocation@example.com",
            phone_number="+919876543210",
        )
        self.login_url = "/api/v1/auth/login/"
        self.refresh_url = reverse("token_refresh")
        self.current_user_url = reverse("users-getcurrentuser")

    def _post(self, *args, **kwargs):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(*args, **kwargs)

    def _put(self, *args, **kwargs):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.put(*args, **kwargs)

    def _login(self, user=None, password=None):
        user = user or self.user
        response = self._post(
            self.login_url,
            {"username": user.username, "password": password or self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def _refresh(self, refresh):
        return self._post(self.refresh_url, {"refresh": refresh}, format="json")

    def _current_user(self, access):
        return self.client.get(
            self.current_user_url, HTTP_AUTHORIZATION=f"Bearer {access}"
        )

    def _assert_session_active(self, session, user=None):
        user = user or self.user
        response = self._current_user(session["access"])
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["username"], user.username)
        refreshed = self._refresh(session["refresh"])
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK, refreshed.data)
        self.assertEqual(
            self._current_user(refreshed.data["access"]).status_code,
            status.HTTP_200_OK,
        )

    def _assert_session_revoked(self, session):
        self.assertEqual(
            self._current_user(session["access"]).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        response = self._refresh(session["refresh"])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def _prepare_sessions(self):
        sessions = [self._login(), self._login()]
        rotated = self._refresh(sessions[-1]["refresh"])
        self.assertEqual(rotated.status_code, status.HTTP_200_OK, rotated.data)
        sessions.append(rotated.data)
        for session in sessions:
            self.assertEqual(
                self._current_user(session["access"]).status_code,
                status.HTTP_200_OK,
            )
        other_user = self.create_user_with_password(
            self.password, username="unaffected_user", phone_number="+919876543211"
        )
        return sessions, other_user, self._login(other_user)

    def _assert_password_change_revokes_sessions(self, sessions, other_user, other):
        for index, session in enumerate(sessions):
            with self.subTest(session=index):
                self._assert_session_revoked(session)
        self._assert_session_active(self._login(password=self.new_password))
        self._assert_session_active(other, other_user)

    def _send_reset_otp(self):
        response = self._post(
            reverse("otp-password-reset-send"),
            {"phone_number": self.user.phone_number},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return (
            MobileOTP.objects.filter(phone_number=self.user.phone_number, is_used=False)
            .latest("created_date")
            .otp
        )

    def _confirm_reset_otp(self, otp):
        return self._post(
            reverse("otp-password-reset-confirm"),
            {
                "phone_number": self.user.phone_number,
                "otp": otp,
                "password": self.new_password,
            },
            format="json",
        )

    def test_otp_reset_revokes_access_and_refresh_for_all_sessions(self):
        sessions, other_user, other = self._prepare_sessions()
        response = self._confirm_reset_otp(self._send_reset_otp())
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self._assert_password_change_revokes_sessions(sessions, other_user, other)

    def test_email_reset_revokes_access_and_refresh_for_all_sessions(self):
        sessions, other_user, other = self._prepare_sessions()
        response = self._post(
            reverse("password_reset_confirm"),
            {
                "token": generate_password_reset_token(self.user),
                "password": self.new_password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self._assert_password_change_revokes_sessions(sessions, other_user, other)

    def test_authenticated_password_change_revokes_all_sessions(self):
        sessions, other_user, other = self._prepare_sessions()
        response = self._put(
            reverse("change_password_view"),
            {"old_password": self.password, "new_password": self.new_password},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {sessions[0]['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self._assert_password_change_revokes_sessions(sessions, other_user, other)

    def test_failed_otp_reset_keeps_existing_session_valid(self):
        session = self._login()
        otp = self._send_reset_otp()
        invalid_otp = "0" * len(otp) if set(otp) != {"0"} else "1" * len(otp)
        response = self._confirm_reset_otp(invalid_otp)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self._assert_session_active(session)

    def test_failed_email_reset_keeps_existing_session_valid(self):
        session = self._login()
        response = self._post(
            reverse("password_reset_confirm"),
            {"token": "invalid-token", "password": self.new_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self._assert_session_active(session)

    def test_failed_password_change_keeps_existing_session_valid(self):
        session = self._login()
        response = self._put(
            reverse("change_password_view"),
            {"old_password": "wrong-password", "new_password": self.new_password},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {session['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self._assert_session_active(session)

    def test_tokens_without_password_claim_are_rejected(self):
        refresh = RefreshToken(self._login()["refresh"])
        del refresh[api_settings.REVOKE_TOKEN_CLAIM]
        self._assert_session_revoked(
            {"refresh": str(refresh), "access": str(refresh.access_token)}
        )

    def test_refresh_rejects_inactive_and_deleted_users(self):
        session = self._login()
        for field, value in (("is_active", False), ("deleted", True)):
            with self.subTest(field=field):
                original = getattr(self.user, field)
                setattr(self.user, field, value)
                self.user.save(update_fields=[field])
                response = self._refresh(session["refresh"])
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                self.assertNotIn("access", response.data)
                setattr(self.user, field, original)
                self.user.save(update_fields=[field])

    def test_refresh_rejects_missing_user(self):
        refresh = RefreshToken(self._login()["refresh"])
        refresh[api_settings.USER_ID_CLAIM] = str(uuid.uuid4())
        response = self._refresh(str(refresh))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_password_reset_revokes_pending_mfa_login(self):
        self.user.totp_secret = "JBSWY3DPEHPK3PXP"
        self.user.mfa_settings = {"totp": {"enabled": True}}
        self.user.save(update_fields=["totp_secret", "mfa_settings"])
        temp_token = self._login()["temp_token"]
        response = self._confirm_reset_otp(self._send_reset_otp())
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        response = self._post(
            reverse("mfa-login"),
            {
                "method": "totp",
                "code": TOTP(self.user.totp_secret).now(),
                "temp_token": temp_token,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("access", response.data)

        fresh_temp_token = self._login(password=self.new_password)["temp_token"]
        response = self._post(
            reverse("mfa-login"),
            {
                "method": "totp",
                "code": TOTP(self.user.totp_secret).now(),
                "temp_token": fresh_temp_token,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self._assert_session_active(response.data)

    def test_password_reset_during_mfa_cannot_issue_usable_tokens(self):
        self.user.totp_secret = "JBSWY3DPEHPK3PXP"
        self.user.mfa_settings = {"totp": {"enabled": True}}
        self.user.save(update_fields=["totp_secret", "mfa_settings"])
        temp_token = self._login()["temp_token"]

        def reset_password(request, user_id):
            # Simulate a reset after the temporary token's password was checked.
            User.objects.filter(external_id=user_id).update(
                password=make_password(self.new_password)
            )

        with patch(
            "care.emr.api.viewsets.mfa_login.check_mfa_user_rate_limit",
            side_effect=reset_password,
        ):
            response = self._post(
                reverse("mfa-login"),
                {
                    "method": "totp",
                    "code": TOTP(self.user.totp_secret).now(),
                    "temp_token": temp_token,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertNotIn("access", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
