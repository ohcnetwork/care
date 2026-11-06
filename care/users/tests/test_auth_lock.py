from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.urls import reverse
from pyotp import TOTP
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from care.emr.utils.reset_password import generate_password_reset_token
from care.facility.models.patient import MobileOTP
from care.users.locks import lock_user_auth
from care.users.models import User
from care.utils.lock import ObjectLocked
from care.utils.tests.base import CareAPITestBase


class UserAuthLockTests(CareAPITestBase):
    password = "OldSecret173!"
    new_password = "NewSecret284!"
    backup_code = "12345678"

    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = self.create_user_with_password(
            self.password,
            username="auth_lock_user",
            phone_number="+919876543210",
            preferences={},
        )

    def _redis_lock(self, user=None):
        user = user or self.user
        return cache.lock(
            f"lock:user_auth:{user.external_id}", timeout=settings.LOCK_TIMEOUT
        )

    def _post(self, url, data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, data, format="json")

    def _login(self, user=None, password=None):
        user = user or self.user
        response = self._post(
            "/api/v1/auth/login/",
            {"username": user.username, "password": password or self.password},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def _enable_backup_login(self):
        self.user.totp_secret = "JBSWY3DPEHPK3PXP"
        self.user.mfa_settings = {
            "totp": {
                "enabled": True,
                "backup_codes": [
                    {"code": make_password(self.backup_code), "used": False}
                ],
            }
        }
        self.user.save(update_fields=["totp_secret", "mfa_settings"])
        return self._login()["temp_token"]

    def _backup_login(self, temp_token):
        return self._post(
            reverse("mfa-login"),
            {
                "method": "backup",
                "code": self.backup_code,
                "temp_token": temp_token,
            },
        )

    def _assert_backup_unused(self):
        self.user.refresh_from_db()
        self.assertFalse(self.user.mfa_settings["totp"]["backup_codes"][0]["used"])

    def test_lock_is_held_until_transaction_commits(self):
        contender = self._redis_lock()
        with self.captureOnCommitCallbacks(execute=True):
            with lock_user_auth(self.user.external_id):
                self.assertFalse(contender.acquire(blocking=False))
            self.assertFalse(contender.acquire(blocking=False))

        self.assertTrue(contender.acquire(blocking=False))
        contender.release()

    def test_exception_rolls_back_writes_before_releasing_lock(self):
        with self.assertRaises(ValidationError), lock_user_auth(self.user.external_id):
            self.user.preferences = {"rolled_back": True}
            self.user.save(update_fields=["preferences"])
            raise ValidationError("Abort authentication")

        self.user.refresh_from_db()
        self.assertEqual(self.user.preferences, {})
        contender = self._redis_lock()
        self.assertTrue(contender.acquire(blocking=False))
        contender.release()

    def test_lost_lease_rolls_back_and_does_not_release_new_owner(self):
        successor = self._redis_lock()
        with self.assertRaises(ObjectLocked), lock_user_auth(self.user.external_id):
            self.user.preferences = {"rolled_back": True}
            self.user.save(update_fields=["preferences"])
            cache.delete(f"lock:user_auth:{self.user.external_id}")
            self.assertTrue(successor.acquire(blocking=False))

        self.assertTrue(successor.owned())
        successor.release()
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferences, {})

    def test_redis_failure_does_not_enter_protected_operation(self):
        with (
            patch("care.users.locks.cache.lock", side_effect=RedisConnectionError),
            self.assertRaises(APIException) as raised,
            lock_user_auth(self.user.external_id),
        ):
            self.fail("Authentication must not proceed without the Redis lock")
        self.assertEqual(
            raised.exception.status_code, status.HTTP_503_SERVICE_UNAVAILABLE
        )

    def test_other_users_have_independent_locks(self):
        other = self.create_user_with_password(self.password)
        with (
            self.captureOnCommitCallbacks(execute=True),
            lock_user_auth(self.user.external_id),
            lock_user_auth(other.external_id),
        ):
            self.assertFalse(self._redis_lock().acquire(blocking=False))
            self.assertFalse(self._redis_lock(other).acquire(blocking=False))

    def test_reset_between_temp_validation_and_lock_does_not_consume_last_code(self):
        temp_token = self._enable_backup_login()

        def reset_password(request, user_id):
            # The reset wins immediately before MFA acquires the shared lock.
            User.objects.filter(external_id=user_id).update(
                password=make_password(self.new_password)
            )

        with patch(
            "care.emr.api.viewsets.mfa_login.check_mfa_user_rate_limit",
            side_effect=reset_password,
        ):
            response = self._backup_login(temp_token)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertNotIn("access", response.data)
        self._assert_backup_unused()
        contender = self._redis_lock()
        self.assertTrue(contender.acquire(blocking=False))
        contender.release()

    def test_reset_between_totp_validation_and_lock_rejects_login(self):
        temp_token = self._enable_backup_login()

        def reset_password(request, user_id):
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
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertNotIn("access", response.data)

    def test_backup_code_can_only_complete_one_login(self):
        temp_token = self._enable_backup_login()
        first = self._backup_login(temp_token)
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        second = self._backup_login(temp_token)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST, second.data)
        self.assertNotIn("access", second.data)

    def test_token_issuance_failure_does_not_consume_backup_code(self):
        temp_token = self._enable_backup_login()
        with patch(
            "care.emr.api.viewsets.mfa_login.create_auth_response",
            side_effect=ValidationError("Token issuance failed"),
        ):
            response = self._backup_login(temp_token)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self._assert_backup_unused()
        retry = self._backup_login(temp_token)
        self.assertEqual(retry.status_code, status.HTTP_200_OK, retry.data)

    def test_contention_rejects_mfa_without_consuming_backup_code(self):
        temp_token = self._enable_backup_login()
        holder = self._redis_lock()
        self.assertTrue(holder.acquire(blocking=False))
        try:
            response = self._backup_login(temp_token)
            self.assertEqual(
                response.status_code, status.HTTP_423_LOCKED, response.data
            )
            self._assert_backup_unused()
            self.assertTrue(holder.owned())
        finally:
            holder.release()

    def test_contention_rejects_password_changes_without_changing_password(self):
        session = self._login()
        reset_token = generate_password_reset_token(self.user)
        otp = "45612"
        MobileOTP.objects.create(phone_number=self.user.phone_number, otp=otp)
        holder = self._redis_lock()
        self.assertTrue(holder.acquire(blocking=False))
        try:
            requests = (
                (
                    "post",
                    reverse("password_reset_confirm"),
                    {"token": reset_token, "password": self.new_password},
                    {},
                ),
                (
                    "post",
                    reverse("otp-password-reset-confirm"),
                    {
                        "phone_number": self.user.phone_number,
                        "otp": otp,
                        "password": self.new_password,
                    },
                    {},
                ),
                (
                    "put",
                    reverse("change_password_view"),
                    {"old_password": self.password, "new_password": self.new_password},
                    {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"},
                ),
            )
            for method, url, data, kwargs in requests:
                with self.subTest(url=url), self.captureOnCommitCallbacks(execute=True):
                    response = getattr(self.client, method)(
                        url, data, format="json", **kwargs
                    )
                    self.assertEqual(
                        response.status_code, status.HTTP_423_LOCKED, response.data
                    )
                    self.user.refresh_from_db()
                    self.assertTrue(self.user.check_password(self.password))
                    self.assertTrue(holder.owned())
        finally:
            holder.release()

    def test_password_mutations_revoke_access_and_refresh_for_all_sessions(self):
        unaffected_session = self._login()
        for index, flow in enumerate(("email", "otp", "change")):
            with self.subTest(flow=flow):
                user = self.create_user_with_password(
                    self.password,
                    username=f"reset_{flow}_user",
                    phone_number=f"+91987654321{index}",
                )
                sessions = [self._login(user), self._login(user)]
                rotated = self._post(
                    reverse("token_refresh"), {"refresh": sessions[-1]["refresh"]}
                )
                self.assertEqual(rotated.status_code, status.HTTP_200_OK, rotated.data)
                sessions.append(rotated.data)

                if flow == "email":
                    response = self._post(
                        reverse("password_reset_confirm"),
                        {
                            "token": generate_password_reset_token(user),
                            "password": self.new_password,
                        },
                    )
                elif flow == "otp":
                    otp = "45612"
                    MobileOTP.objects.create(phone_number=user.phone_number, otp=otp)
                    response = self._post(
                        reverse("otp-password-reset-confirm"),
                        {
                            "phone_number": user.phone_number,
                            "otp": otp,
                            "password": self.new_password,
                        },
                    )
                else:
                    with self.captureOnCommitCallbacks(execute=True):
                        response = self.client.put(
                            reverse("change_password_view"),
                            {
                                "old_password": self.password,
                                "new_password": self.new_password,
                            },
                            format="json",
                            HTTP_AUTHORIZATION=f"Bearer {sessions[0]['access']}",
                        )
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data
                )

                for session in sessions:
                    current_user = self.client.get(
                        reverse("users-getcurrentuser"),
                        HTTP_AUTHORIZATION=f"Bearer {session['access']}",
                    )
                    self.assertEqual(
                        current_user.status_code,
                        status.HTTP_403_FORBIDDEN,
                        current_user.data,
                    )
                    refresh = self._post(
                        reverse("token_refresh"), {"refresh": session["refresh"]}
                    )
                    self.assertEqual(
                        refresh.status_code,
                        status.HTTP_401_UNAUTHORIZED,
                        refresh.data,
                    )
                    self.assertNotIn("access", refresh.data)

                fresh = self._login(user, self.new_password)
                for session in (fresh, unaffected_session):
                    current_user = self.client.get(
                        reverse("users-getcurrentuser"),
                        HTTP_AUTHORIZATION=f"Bearer {session['access']}",
                    )
                    self.assertEqual(
                        current_user.status_code, status.HTTP_200_OK, current_user.data
                    )
                    refreshed = self._post(
                        reverse("token_refresh"), {"refresh": session["refresh"]}
                    )
                    self.assertEqual(
                        refreshed.status_code, status.HTTP_200_OK, refreshed.data
                    )
