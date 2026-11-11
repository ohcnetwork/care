import time
from unittest.mock import patch
from urllib.parse import urlsplit

from django.contrib import admin
from django.contrib.auth import SESSION_KEY
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import path, reverse
from freezegun import freeze_time
from pyotp import TOTP, random_base32

from care.users.models import User

urlpatterns = [path("admin/", admin.site.urls)]


@override_settings(
    ROOT_URLCONF=__name__,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    },
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    DJANGO_RATE_LIMIT="100/m",
    DISABLE_RATELIMIT=True,
)
class AdminMFATests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        delete_pattern_patch = patch.object(cache, "delete_pattern", create=True)
        delete_pattern_patch.start()
        self.addCleanup(delete_pattern_patch.stop)
        self.password = "admin-test-password"
        self.secret = random_base32()
        self.user = User.objects.create_superuser(
            username="testadmin",
            email="admin@example.com",
            password=self.password,
            phone_number="+919876543210",
            totp_secret=self.secret,
            mfa_settings={"totp": {"enabled": True}},
        )
        self.login_url = reverse("admin:login")
        self.totp_url = reverse("admin:totp")
        self.index_url = reverse("admin:index")

    def start_challenge(self, client=None, **extra):
        client = client or self.client
        response = client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password, **extra},
        )
        self.assertRedirects(response, self.totp_url, fetch_redirect_response=False)
        self.assertNotIn(SESSION_KEY, client.session)
        return response

    def verify(self, client=None, **extra):
        return (client or self.client).post(
            self.totp_url, {"code": TOTP(self.secret).now()}, **extra
        )

    def assert_challenge_rejected(self):
        response = self.verify()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response.url).path, self.login_url)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_password_login_requires_totp_before_creating_authenticated_session(self):
        self.start_challenge()

        response = self.client.get(self.totp_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("code", response.context["form"].fields)
        self.assertNotIn(SESSION_KEY, self.client.session)

        response = self.verify()
        self.assertRedirects(response, self.index_url)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertNotIn("admin_mfa_pending", self.client.session)

    def test_invalid_totp_does_not_authenticate(self):
        self.start_challenge()

        response = self.client.post(self.totp_url, {"code": "invalid"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn(SESSION_KEY, self.client.session)

    @freeze_time("2026-11-09 06:00:00")
    def test_incorrect_six_digit_totp_does_not_authenticate(self):
        self.start_challenge()
        totp = TOTP(self.secret)
        accepted_codes = {
            totp.at(time.time(), counter_offset=offset) for offset in (-1, 0, 1)
        }
        incorrect_code = next(
            f"{number:06d}"
            for number in range(1_000_000)
            if f"{number:06d}" not in accepted_codes
        )

        response = self.client.post(self.totp_url, {"code": incorrect_code})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_totp_code_cannot_be_reused_for_another_login(self):
        other_client = Client()
        self.start_challenge()
        self.start_challenge(other_client)
        code = TOTP(self.secret).now()

        self.assertRedirects(
            self.client.post(self.totp_url, {"code": code}), self.index_url
        )
        response = other_client.post(self.totp_url, {"code": code})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn(SESSION_KEY, other_client.session)

    def test_admin_views_are_inaccessible_before_totp_verification(self):
        self.start_challenge()

        for url in (self.index_url, reverse("admin:users_user_changelist")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(urlsplit(response.url).path, self.login_url)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_existing_authenticated_session_still_requires_totp(self):
        self.client.force_login(self.user)

        response = self.client.get(self.index_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("code", response.context["form"].fields)

    def test_secret_change_requires_verification_again_for_verified_session(self):
        self.start_challenge()
        self.assertRedirects(self.verify(), self.index_url)
        self.secret = random_base32()
        self.user.totp_secret = self.secret
        self.user.save(update_fields=["totp_secret"])

        response = self.client.get(self.index_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("code", response.context["form"].fields)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertRedirects(self.verify(), self.index_url)

    def test_logout_clears_totp_verification(self):
        self.start_challenge()
        self.assertRedirects(self.verify(), self.index_url)
        self.assertIn("admin_mfa_verified", self.client.session)

        self.client.post(reverse("admin:logout"))

        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn("admin_mfa_verified", self.client.session)
        self.start_challenge()

    def test_totp_requires_a_password_challenge(self):
        self.assert_challenge_rejected()

    def test_expired_challenge_requires_password_again(self):
        self.start_challenge()
        session = self.client.session
        session["admin_mfa_pending"]["issued_at"] = time.time() - 301
        session.save()

        self.assert_challenge_rejected()

    def test_password_change_invalidates_pending_challenge(self):
        self.start_challenge()
        self.user.set_password("changed-password")
        self.user.save(update_fields=["password"])

        self.assert_challenge_rejected()

    def test_secret_change_invalidates_pending_challenge(self):
        self.start_challenge()
        self.user.totp_secret = random_base32()
        self.user.save(update_fields=["totp_secret"])

        self.assert_challenge_rejected()

    def test_deactivated_user_cannot_complete_challenge(self):
        self.start_challenge()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.assert_challenge_rejected()

    def test_removed_staff_permission_prevents_completing_challenge(self):
        self.start_challenge()
        self.user.is_staff = False
        self.user.save(update_fields=["is_staff"])

        self.assert_challenge_rejected()

    def test_disabling_mfa_invalidates_pending_challenge(self):
        self.start_challenge()
        self.user.mfa_settings = {"totp": {"enabled": False}}
        self.user.save(update_fields=["mfa_settings"])

        self.assert_challenge_rejected()

    def test_mfa_without_secret_cannot_authenticate(self):
        self.user.totp_secret = None
        self.user.save(update_fields=["totp_secret"])
        self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
        )
        response = self.client.post(self.totp_url, {"code": "123456"})

        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotEqual(response.status_code, 500)

    def test_malformed_stored_secret_does_not_authenticate_or_crash(self):
        self.user.totp_secret = "not-valid-base32!"
        self.user.save(update_fields=["totp_secret"])
        self.start_challenge()

        response = self.client.post(self.totp_url, {"code": "123456"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_safe_next_url_is_preserved_through_totp(self):
        next_url = reverse("admin:users_user_changelist")
        self.start_challenge(next=next_url)

        self.assertRedirects(self.verify(), next_url)

    def test_external_next_url_is_ignored(self):
        self.start_challenge(next="https://example.org/phishing")

        self.assertRedirects(self.verify(), self.index_url)

    def test_user_without_mfa_logs_in_normally(self):
        self.user.mfa_settings = {}
        self.user.save(update_fields=["mfa_settings"])

        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(response, self.index_url)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    @override_settings(DJANGO_RATE_LIMIT="2/m")
    def test_password_attempts_are_limited_by_account_across_ips(self):
        for index, expected_status in enumerate((200, 200, 429)):
            response = self.client.post(
                self.login_url,
                {"username": self.user.username, "password": "wrong-password"},
                REMOTE_ADDR=f"192.0.2.{index + 1}",
            )
            self.assertEqual(response.status_code, expected_status)
        self.assertNotIn(SESSION_KEY, self.client.session)

    @override_settings(DJANGO_RATE_LIMIT="2/m")
    def test_password_attempts_are_limited_by_ip_across_accounts(self):
        for index, expected_status in enumerate((200, 200, 429)):
            response = self.client.post(
                self.login_url,
                {"username": f"unknown{index}", "password": "wrong-password"},
            )
            self.assertEqual(response.status_code, expected_status)

    @override_settings(DJANGO_RATE_LIMIT="2/m")
    def test_totp_attempts_are_limited_by_account_across_ips(self):
        self.start_challenge()

        for index, expected_status in enumerate((200, 200, 429)):
            response = self.client.post(
                self.totp_url,
                {"code": "invalid"},
                REMOTE_ADDR=f"192.0.2.{index + 1}",
            )
            self.assertEqual(response.status_code, expected_status)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_totp_attempts_are_limited_by_ip_across_accounts(self):
        clients = []
        for index in range(3):
            user = User.objects.create_superuser(
                username=f"otheradmin{index}",
                email=f"admin{index}@example.com",
                password=self.password,
                phone_number="+919876543210",
                totp_secret=random_base32(),
                mfa_settings={"totp": {"enabled": True}},
            )
            client = Client()
            response = client.post(
                self.login_url, {"username": user.username, "password": self.password}
            )
            self.assertRedirects(response, self.totp_url, fetch_redirect_response=False)
            clients.append(client)

        with override_settings(DJANGO_RATE_LIMIT="2/m"):
            for client, expected_status in zip(clients, (200, 200, 429), strict=True):
                response = client.post(self.totp_url, {"code": "invalid"})
                self.assertEqual(response.status_code, expected_status)

    @override_settings(DJANGO_RATE_LIMIT="2/m")
    def test_get_requests_do_not_consume_login_or_totp_attempts(self):
        for _ in range(3):
            self.assertEqual(self.client.get(self.login_url).status_code, 200)
        self.start_challenge()
        for _ in range(3):
            self.assertEqual(self.client.get(self.totp_url).status_code, 200)

        self.assertRedirects(self.verify(), self.index_url)

    def test_login_and_totp_require_csrf_tokens(self):
        client = Client(enforce_csrf_checks=True)
        client.get(self.login_url)
        credentials = {"username": self.user.username, "password": self.password}
        self.assertEqual(client.post(self.login_url, credentials).status_code, 403)

        response = client.post(
            self.login_url,
            {**credentials, "csrfmiddlewaretoken": client.cookies["csrftoken"].value},
        )
        self.assertRedirects(response, self.totp_url, fetch_redirect_response=False)

        self.assertEqual(self.verify(client).status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)
