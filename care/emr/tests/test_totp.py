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
        self.assertTrue(self.user.is_mfa_enabled())

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

    def test_totp_setup_with_invalid_password(self):
        """Test TOTP setup fails with invalid password"""
        response = self.client.post(
            self.totp_setup_url, {"password": "wrong_password"}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.totp_secret)

    def test_totp_setup_when_already_enabled(self):
        """Test TOTP setup fails when already enabled"""
        self._setup_and_verify_totp()

        response = self.client.post(
            self.totp_setup_url, {"password": self.password}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_totp_verify_with_invalid_code(self):
        """Test TOTP verify fails with invalid code"""
        self.client.post(
            self.totp_setup_url, {"password": self.password}, format="json"
        )

        response = self.client.post(
            self.totp_verify_url, {"code": "000000"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_mfa_enabled())

    def test_totp_verify_without_setup(self):
        """Test TOTP verify fails when TOTP is not set up"""
        response = self.client.post(
            self.totp_verify_url, {"code": "123456"}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_totp_disable_with_invalid_password(self):
        """Test TOTP disable fails with invalid password"""
        self._setup_and_verify_totp()

        response = self.client.post(
            self.totp_disable_url, {"password": "wrong_password"}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_mfa_enabled())

    def test_totp_disable_when_not_enabled(self):
        """Test TOTP disable fails when not enabled"""
        response = self.client.post(
            self.totp_disable_url, {"password": self.password}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_regenerate_backup_codes_with_invalid_password(self):
        """Test regenerate backup codes fails with invalid password"""
        self._setup_and_verify_totp()

        response = self.client.post(
            self.totp_regenerate_backup_codes_url,
            {"password": "wrong_password"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_totp_verify_with_already_enabled(self):
        """Test TOTP verify fails when already enabled"""
        self._setup_and_verify_totp()

        secret_key = self.user.totp_secret
        totp = TOTP(secret_key)
        code = totp.now()

        response = self.client.post(self.totp_verify_url, {"code": code}, format="json")

        self.assertEqual(response.status_code, 400)
