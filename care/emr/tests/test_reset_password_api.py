import hashlib

import jwt
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from care.utils.tests.base import CareAPITestBase


class ResetPasswordAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser", email="testuser@example.com")
        self.reset_password_request_url = reverse("password_reset_request")
        self.reset_password_confirm_url = reverse("password_reset_confirm")
        self.reset_password_check_url = reverse("password_reset_check")
        cache.clear()

    def extract_token_from_email(self, email_body):
        """Extract token from reset password email body"""
        import re

        match = re.search(r'/password_reset/([^\s"<>]+)', email_body)
        if match:
            return match.group(1)
        return None

    def test_reset_password_request_with_valid_username(self):
        """
        Test the password reset request with a valid username to generate valid token via email.
        """
        response = self.client.post(
            self.reset_password_request_url, {"username": "testuser"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["testuser@example.com"])
        self.assertIn("password reset for care", mail.outbox[0].subject.lower())

    def test_reset_password_request_with_invalid_username(self):
        """
        Test the password reset request with an invalid username.
        Returns 200 OK inorder to prevent information leakage.
        """
        response = self.client.post(
            self.reset_password_request_url, {"username": "invaliduser"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.data, {"status": "OK"})

    def test_reset_password_request_with_information_leakage_true(self):
        """
        Test that shows whether the user existence otherwise username validation error message
        """
        with override_settings(DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE=False):
            response = self.client.post(
                self.reset_password_request_url,
                {"username": "invalidUser"},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertContains(
                response,
                "There is no active user associated with this username or the password cannot be changed",
                status_code=400,
            )

    def test_reset_password_request_without_username(self):
        """
        Test that check for the username parameter in the request
        """
        response = self.client.post(self.reset_password_request_url, {}, format="json")
        self.assertContains(
            response, "Missing required parameter username.", status_code=400
        )

    def test_reset_password_check_with_valid_token(self):
        """
        Test the password reset check with a valid token.
        """
        self.client.post(
            self.reset_password_request_url, {"username": "testuser"}, format="json"
        )
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        token = self.extract_token_from_email(email_body)
        self.assertIsNotNone(token)

        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "OK"})

    def test_reset_password_check_with_invalid_token(self):
        """
        Test the password reset check with an invalid token.
        """
        token = str(
            jwt.encode({"some": "payload"}, settings.SECRET_KEY, algorithm="HS256")
        )
        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid token", status_code=400)

    def test_reset_password_check_with_missing_token(self):
        """
        Test the password reset confirm with a missing token.
        """
        response = self.client.post(self.reset_password_check_url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Missing required parameter token", status_code=400
        )

    def test_reset_password_check_invalid_password_hash(self):
        """
        Test that checks whether the payload password hash is valid.
        This missmatch cause due to change in passowrd
        """
        token = str(
            jwt.encode(
                {"username": "testuser", "password_hash": "invalid_hash"},
                settings.SECRET_KEY,
                algorithm="HS256",
            )
        )
        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertContains(
            response, "Token invalid due to password change", status_code=400
        )

    def test_reset_password_check_with_invalid_token_type(self):
        """
        Test that checks whether the payload token type is valid.
        """
        secret_key = settings.SECRET_KEY
        password_hash = hashlib.sha256(
            (self.user.password + secret_key).encode()
        ).hexdigest()
        token = str(
            jwt.encode(
                {
                    "username": "testuser",
                    "type": "invalid_type",
                    "password_hash": password_hash,
                },
                settings.SECRET_KEY,
                algorithm="HS256",
            )
        )
        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertContains(response, "Invalid token type", status_code=400)

    def test_reset_password_check_with_token_user_mismatch(self):
        """
        Test that checks whether the payload user matches the token user.
        """
        another_user = self.create_user(
            username="anotheruser", email="anotheruser@example.com"
        )
        secret_key = settings.SECRET_KEY
        password_hash = hashlib.sha256(
            (self.user.password + secret_key).encode()
        ).hexdigest()
        token = str(
            jwt.encode(
                {
                    "username": "testuser",
                    "type": "password_reset",
                    "password_hash": password_hash,
                    "sub": str(another_user.external_id),
                },
                settings.SECRET_KEY,
                algorithm="HS256",
            )
        )
        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertContains(response, "Token doesn't match user", status_code=400)

    def test_reset_password_check_with_expired_token(self):
        """
        Test that checks whether the token is expired.
        """
        import datetime

        expired_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        token = str(
            jwt.encode({"exp": expired_time}, settings.SECRET_KEY, algorithm="HS256")
        )
        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertContains(response, "Token has expired", status_code=400)

    def test_reset_password_check_with_invalid_user(self):
        """
        Test that checks whether the user in the token exists.
        """
        token = str(
            jwt.encode(
                {"username": "nonexistentuser"}, settings.SECRET_KEY, algorithm="HS256"
            )
        )
        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertContains(response, "User not found", status_code=400)

    def test_reset_password_check_with_malformed_token(self):
        """
        Test that checks whether the token is malformed.
        """
        token = "thisisnotavalidjwttoken"
        response = self.client.post(
            self.reset_password_check_url, {"token": token}, format="json"
        )
        self.assertContains(response, "Error verifying token", status_code=400)

    def test_reset_password_confirm_with_valid_token(self):
        """
        Test the password reset confirm with a valid token.
        """
        self.client.post(
            self.reset_password_request_url, {"username": "testuser"}, format="json"
        )
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        token = self.extract_token_from_email(email_body)
        self.assertIsNotNone(token)

        new_password = "password@123"
        response = self.client.post(
            self.reset_password_confirm_url,
            {"token": token, "password": new_password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "OK"})

        login_url = "/api/v1/auth/login/"
        login_response = self.client.post(
            login_url,
            {"username": "testuser", "password": new_password},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

    def test_reset_password_confirm_with_invalid_token(self):
        """
        Test the password reset confirm with an invalid token.
        """
        token = str(
            jwt.encode({"some": "payload"}, settings.SECRET_KEY, algorithm="HS256")
        )
        new_password = "newpassword@123"
        response = self.client.post(
            self.reset_password_confirm_url,
            {"token": token, "password": new_password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid token", status_code=400)

    def test_reset_password_confirm_with_missing_parameters(self):
        """
        Test the password reset confirm with missing parameters.
        """
        response = self.client.post(
            self.reset_password_confirm_url, {"password": "hello@123"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Missing required parameter token or password.", status_code=400
        )

    def test_reset_password_confirm_with_weak_password(self):
        """
        Test the password reset confirm with a weak password.
        """
        self.client.post(
            self.reset_password_request_url, {"username": "testuser"}, format="json"
        )
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        token = self.extract_token_from_email(email_body)
        self.assertIsNotNone(token)

        weak_password = "123"
        response = self.client.post(
            self.reset_password_confirm_url,
            {"token": token, "password": weak_password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "This password is too short. It must contain at least 8 characters.",
            str(response.data),
        )

    def test_reset_password_confirm_with_password_with_only_numbers(self):
        """
        Test the password reset confirm with a password that contains only numbers.
        """
        self.client.post(
            self.reset_password_request_url, {"username": "testuser"}, format="json"
        )
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        token = self.extract_token_from_email(email_body)
        self.assertIsNotNone(token)

        weak_password = "123323432"
        response = self.client.post(
            self.reset_password_confirm_url,
            {"token": token, "password": weak_password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("This password is entirely numeric.", str(response.data))

    def test_password_reset_confirm_with_password_too_common(self):
        """
        Test the password reset confirm with a commonly used password.
        """
        self.client.post(
            self.reset_password_request_url, {"username": "testuser"}, format="json"
        )
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        token = self.extract_token_from_email(email_body)
        self.assertIsNotNone(token)

        common_password = "password123"
        response = self.client.post(
            self.reset_password_confirm_url,
            {"token": token, "password": common_password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("This password is too common.", str(response.data))

    def test_password_request_rate_limiting(self):
        """
        Test the rate limiting on password reset requests.
        """
        with override_settings(DISABLE_RATELIMIT=False):
            for _i in range(10):
                response = self.client.post(
                    self.reset_password_request_url,
                    {"username": "testuser"},
                    format="json",
                )
            response = self.client.post(
                self.reset_password_request_url,
                {"username": "testuser"},
                format="json",
            )
            self.assertEqual(response.status_code, 429)
            self.assertContains(
                response,
                "Too many requests. Please try again later.",
                status_code=429,
            )

    def test_password_check_rate_limiting(self):
        """
        Test the rate limiting on password reset token checks.
        """
        with override_settings(DISABLE_RATELIMIT=False):
            self.client.post(
                self.reset_password_request_url, {"username": "testuser"}, format="json"
            )
            self.assertEqual(len(mail.outbox), 1)
            email_body = mail.outbox[0].body
            token = self.extract_token_from_email(email_body)
            self.assertIsNotNone(token)
            for _i in range(10):
                response = self.client.post(
                    self.reset_password_check_url,
                    {"token": token},
                    format="json",
                )
                self.assertEqual(response.status_code, 200)
            response = self.client.post(
                self.reset_password_check_url,
                {"token": token},
                format="json",
            )
            self.assertEqual(response.status_code, 429)
            self.assertContains(
                response,
                "Too many requests. Please try again later.",
                status_code=429,
            )

    def test_password_confirm_rate_limiting(self):
        """
        Test the rate limiting on password reset confirmations.
        """
        with override_settings(DISABLE_RATELIMIT=False):
            self.client.post(
                self.reset_password_request_url, {"username": "testuser"}, format="json"
            )
            self.assertEqual(len(mail.outbox), 1)
            email_body = mail.outbox[0].body
            token = self.extract_token_from_email(email_body)
            self.assertIsNotNone(token)
            new_password = "password@123"
            for _i in range(10):
                response = self.client.post(
                    self.reset_password_confirm_url,
                    {"token": token, "password": new_password},
                    format="json",
                )
            response = self.client.post(
                self.reset_password_confirm_url,
                {"token": token, "password": new_password},
                format="json",
            )
            self.assertEqual(response.status_code, 429)
            self.assertContains(
                response,
                "Too many requests. Please try again later.",
                status_code=429,
            )
