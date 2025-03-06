from django.urls import reverse
from pyotp import TOTP

from care.utils.tests.base import CareAPITestBase


class TestTOTPViewSet(CareAPITestBase):
    def setUp(self):
        self.totp_setup_url = reverse("mfa-totp-setup")
        self.totp_verify_url = reverse("mfa-totp-verify")
        self.totp_disable_url = reverse("mfa-totp-disable")
        self.totp_regenerate_backup_codes_url = reverse(
            "mfa-totp-regenerate-backup-codes"
        )

        self.password = "testpassword123"
        self.user = self.create_user_with_password(self.password)
        self.client.force_authenticate(user=self.user)

    def _setup_and_verify_totp(self):
        """Set up TOTP, verify it, and return the secret key and backup codes"""
        setup_response = self.client.post(
            self.totp_setup_url, {"password": self.password}, format="json"
        )
        self.assertEqual(setup_response.status_code, 200)
        secret_key = setup_response.data["secret_key"]

        totp = TOTP(secret_key)
        code = totp.now()
        verify_response = self.client.post(
            self.totp_verify_url, {"code": code}, format="json"
        )
        self.assertEqual(verify_response.status_code, 200)

        return secret_key, verify_response.data["backup_codes"]

    def test_totp_setup(self):
        """Test setting up TOTP for a user"""
        response = self.client.post(
            self.totp_setup_url, {"password": self.password}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("uri", response.data)
        self.assertIn("secret_key", response.data)

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.totp_secret)

    def test_totp_verify(self):
        """Test verifying TOTP code and enabling 2FA"""

        _, backup_codes = self._setup_and_verify_totp()

        self.assertEqual(len(backup_codes), 10)
        self.user.refresh_from_db()
        self.assertTrue(self.user.mfa_settings.get("totp", {}).get("enabled", False))

    def test_totp_disable(self):
        """Test disabling TOTP-based 2FA"""

        self._setup_and_verify_totp()

        disable_response = self.client.post(
            self.totp_disable_url, {"password": self.password}, format="json"
        )

        self.assertEqual(disable_response.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.mfa_settings.get("totp", {}).get("enabled", True))
        self.assertIsNone(self.user.totp_secret)

    def test_regenerate_backup_codes(self):
        """Test regenerating backup codes"""

        _, original_backup_codes = self._setup_and_verify_totp()

        regenerate_response = self.client.post(
            self.totp_regenerate_backup_codes_url,
            {"password": self.password},
            format="json",
        )

        self.assertEqual(regenerate_response.status_code, 200)
        self.assertIn("backup_codes", regenerate_response.data)
        new_backup_codes = regenerate_response.data["backup_codes"]
        self.assertEqual(len(new_backup_codes), 10)

        self.assertNotEqual(set(original_backup_codes), set(new_backup_codes))

        self.user.refresh_from_db()
        self.assertEqual(len(self.user.mfa_settings["totp"]["backup_codes"]), 10)
