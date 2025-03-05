from datetime import timedelta, timezone

from django.urls import reverse
from pyotp import TOTP

from care.utils.tests.base import CareAPITestBase


class TestMFALoginViewSet(CareAPITestBase):
    def setUp(self):
        self.mfa_login_url = reverse("mfa-login")
        self.auth_url = "/api/v1/auth/login/"

        self.user = self.create_user()
        self.password = "testpassword123"

    def _setup_user_with_password(self):
        """Set up user with password"""
        self.user.set_password(self.password)
        self.user.save()
        return self.user

    def _setup_totp_for_user(self, secret_key=None):
        """Set up TOTP for the user"""
        if secret_key is None:
            from pyotp import random_base32

            secret_key = random_base32()

        self.user.totp_secret = secret_key
        self.user.save()
        return secret_key

    def _enable_mfa_with_backup_codes(self, backup_codes=None):
        """Enable MFA with optional backup codes"""
        from django.contrib.auth.hashers import make_password

        if backup_codes is None:
            backup_codes = ["12345678"]

        date = (timezone.now() - timedelta(days=1)).isoformat()
        self.user.mfa_settings = {
            "totp": {
                "enabled": True,
                "enabled_at": date,
                "backup_codes": [
                    {
                        "code": make_password(code),
                        "used": False,
                        "created_at": date,
                    }
                    for code in backup_codes
                ],
            }
        }
        self.user.save()
        return backup_codes

    def _get_temp_token(self):
        """Get a temp token by logging in"""
        login_response = self.client.post(
            self.auth_url,
            {"username": self.user.username, "password": self.password},
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)
        return login_response.data["temp_token"]

    def _perform_mfa_login(self, method, code, temp_token):
        """Perform MFA login with the given method and code"""
        return self.client.post(
            self.mfa_login_url,
            {"method": method, "code": code, "temp_token": temp_token},
            format="json",
        )

    def test_mfa_login_with_totp(self):
        """Test MFA login using TOTP"""
        self._setup_user_with_password()
        secret_key = self._setup_totp_for_user()
        self._enable_mfa_with_backup_codes()

        temp_token = self._get_temp_token()

        totp = TOTP(secret_key)
        code = totp.now()

        response = self._perform_mfa_login("totp", code, temp_token)

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_mfa_login_with_backup_code(self):
        """Test MFA login using backup code"""
        self._setup_user_with_password()
        self._setup_totp_for_user()
        backup_codes = self._enable_mfa_with_backup_codes()

        temp_token = self._get_temp_token()

        response = self._perform_mfa_login("backup", backup_codes[0], temp_token)

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        self.user.refresh_from_db()
        backup_code_entry = self.user.mfa_settings["totp"]["backup_codes"][0]
        self.assertTrue(backup_code_entry["used"])
