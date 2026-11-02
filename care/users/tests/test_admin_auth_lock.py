from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from care.utils.tests.base import CareAPITestBase


class AdminPasswordAuthLockTests(CareAPITestBase):
    password = "OldSecret173!"
    new_password = "NewSecret284!"

    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = self.create_user_with_password(
            self.password, is_staff=True, is_superuser=True
        )
        self.user = self.create_user_with_password(
            self.password,
            mfa_settings={
                "totp": {
                    "enabled": True,
                    "backup_codes": [{"code": "stored-backup-hash", "used": True}],
                }
            },
        )
        self.client.force_login(self.admin)
        self.url = reverse("admin:auth_user_password_change", args=[self.user.pk])
        self.payload = {
            "password1": self.new_password,
            "password2": self.new_password,
            "usable_password": "true",
        }

    def _lock(self):
        return cache.lock(
            f"lock:user_auth:{self.user.external_id}", timeout=settings.LOCK_TIMEOUT
        )

    def test_password_change_rejects_contended_auth_lock(self):
        contender = self._lock()
        self.assertTrue(contender.acquire(blocking=False))
        try:
            response = self.client.post(self.url, self.payload)
            self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password(self.password))
            self.assertTrue(contender.owned())
        finally:
            contender.release()

    def test_password_change_holds_lock_until_commit_and_preserves_mfa(self):
        original_mfa_settings = self.user.mfa_settings
        contender = self._lock()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, self.payload)
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertFalse(contender.acquire(blocking=False))

        self.assertTrue(contender.acquire(blocking=False))
        contender.release()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertEqual(self.user.mfa_settings, original_mfa_settings)
