from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from care.emr.api.viewsets.user import UserViewSet
from care.emr.resources.patient.spec import GenderChoices
from care.users.models import User
from care.utils.tests.base import CareAPITestBase


class UserUpdateLockTests(CareAPITestBase):
    password = "OldSecret173!"

    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = self.create_user_with_password(
            self.password,
            first_name="Original",
            last_name="User",
            phone_number="+919876543210",
            gender=GenderChoices.non_binary,
        )
        self.admin = self.create_super_user()
        self.url = reverse("users-detail", kwargs={"username": self.user.username})
        self.payload = {
            "first_name": "Updated",
            "last_name": self.user.last_name,
            "phone_number": self.user.phone_number,
            "gender": GenderChoices.non_binary,
        }
        self.client.force_authenticate(user=self.user)

    def _lock(self, user=None):
        user = user or self.user
        return cache.lock(
            f"lock:user_auth:{user.external_id}", timeout=settings.LOCK_TIMEOUT
        )

    def _assert_lock_available(self):
        contender = self._lock()
        self.assertTrue(contender.acquire(blocking=False))
        contender.release()

    def test_put_and_patch_reject_contended_target_lock(self):
        holder = self._lock()
        self.assertTrue(holder.acquire(blocking=False))
        try:
            for actor in (self.user, self.admin):
                self.client.force_authenticate(user=actor)
                for method in ("put", "patch"):
                    with self.subTest(actor=actor.pk, method=method):
                        response = getattr(self.client, method)(
                            self.url, self.payload, format="json"
                        )
                        self.assertEqual(
                            response.status_code, status.HTTP_423_LOCKED, response.data
                        )
                        self.user.refresh_from_db()
                        self.assertEqual(self.user.first_name, "Original")
                        self.assertTrue(holder.owned())
        finally:
            holder.release()

    def test_put_and_patch_hold_lock_until_commit(self):
        for method in ("put", "patch"):
            with self.subTest(method=method):
                contender = self._lock()
                with self.captureOnCommitCallbacks(execute=True):
                    response = getattr(self.client, method)(
                        self.url, self.payload, format="json"
                    )
                    self.assertEqual(
                        response.status_code, status.HTTP_200_OK, response.data
                    )
                    self.assertFalse(contender.acquire(blocking=False))
                self._assert_lock_available()
                self.user.refresh_from_db()
                self.assertEqual(self.user.first_name, "Updated")

    def test_admin_update_uses_target_lock_instead_of_admin_lock(self):
        self.client.force_authenticate(user=self.admin)
        actor_lock = self._lock(self.admin)
        self.assertTrue(actor_lock.acquire(blocking=False))
        try:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.put(self.url, self.payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertTrue(actor_lock.owned())
            self._assert_lock_available()
        finally:
            actor_lock.release()

    def test_failed_validation_and_permission_leave_lock_available(self):
        other_user = self.create_user_with_password(self.password)
        cases = (
            (self.user, {"first_name": "Updated"}, status.HTTP_400_BAD_REQUEST),
            (other_user, self.payload, status.HTTP_403_FORBIDDEN),
        )
        for actor, payload, expected_status in cases:
            with self.subTest(actor=actor.pk):
                self.client.force_authenticate(user=actor)
                response = self.client.put(self.url, payload, format="json")
                self.assertEqual(response.status_code, expected_status, response.data)
                self._assert_lock_available()
                self.user.refresh_from_db()
                self.assertEqual(self.user.first_name, "Original")

    def test_update_reloads_auth_state_after_locking(self):
        auth_state = {
            "password": make_password("NewSecret284!"),
            "totp_secret": "CURRENT-SECRET",
            "mfa_settings": {
                "totp": {
                    "enabled": True,
                    "backup_codes": [{"code": "stored-backup-hash", "used": True}],
                }
            },
        }
        get_object = UserViewSet.get_object
        first_lookup = True

        def reset_after_preliminary_lookup(view):
            nonlocal first_lookup
            instance = get_object(view)
            if first_lookup:
                first_lookup = False
                User.objects.filter(pk=instance.pk).update(**auth_state)
            return instance

        with (
            patch.object(
                UserViewSet,
                "get_object",
                autospec=True,
                side_effect=reset_after_preliminary_lookup,
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.put(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        for field, value in auth_state.items():
            self.assertEqual(getattr(self.user, field), value)
        self._assert_lock_available()
