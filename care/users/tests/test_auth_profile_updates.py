from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status

from care.emr.api.viewsets.user import UserViewSet
from care.emr.resources.patient.spec import GenderChoices
from care.users.models import User
from care.utils.tests.base import CareAPITestBase


class UserProfileAuthStateTests(CareAPITestBase):
    password = "OldSecret173!"
    new_password = "NewSecret284!"

    def setUp(self):
        super().setUp()
        self.user = self.create_user_with_password(
            self.password,
            first_name="Original",
            last_name="User",
            phone_number="+919876543210",
            gender=GenderChoices.non_binary,
            totp_secret="OLD-SECRET",
            mfa_settings={"totp": {"enabled": True, "backup_codes": []}},
        )
        self.current_auth_state = {
            "password": make_password(self.new_password),
            "totp_secret": "CURRENT-SECRET",
            "mfa_settings": {
                "totp": {
                    "enabled": True,
                    "backup_codes": [{"code": "stored-backup-hash", "used": True}],
                }
            },
        }

    def _assert_current_auth_state(self):
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        for field, value in self.current_auth_state.items():
            self.assertEqual(getattr(self.user, field), value)
        self.assertTrue(self.user.check_password(self.new_password))

    def test_profile_update_preserves_auth_changes_after_profile_was_loaded(self):
        self.client.force_authenticate(user=self.user)
        perform_update = UserViewSet.perform_update

        def update_auth_then_save_profile(view, instance):
            User.objects.filter(pk=instance.pk).update(**self.current_auth_state)
            return perform_update(view, instance)

        with patch.object(
            UserViewSet,
            "perform_update",
            autospec=True,
            side_effect=update_auth_then_save_profile,
        ):
            response = self.client.put(
                reverse("users-detail", kwargs={"username": self.user.username}),
                {
                    "first_name": "Updated",
                    "last_name": self.user.last_name,
                    "phone_number": self.user.phone_number,
                    "gender": GenderChoices.non_binary,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self._assert_current_auth_state()

    def test_admin_profile_save_preserves_concurrent_auth_changes(self):
        stale_user = User.objects.get(pk=self.user.pk)
        stale_user.first_name = "Updated"
        User.objects.filter(pk=self.user.pk).update(**self.current_auth_state)
        request = RequestFactory().post("/admin/users/")

        admin.site._registry[User].save_model(  # noqa SLF001
            request,
            stale_user,
            SimpleNamespace(changed_data=["first_name", "groups"]),
            change=True,
        )

        self._assert_current_auth_state()
