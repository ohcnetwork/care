from django.conf import settings
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework import status

from care.users.models import User
from care.utils.tests.test_base import TestBase


class TestAuth(TestBase):
    def setUp(self) -> None:
        super().setUp()
        settings.DISABLE_RATELIMIT = True

    def test_login(self):
        """Testing login API"""

        # Testing with missing fields
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": self.user.username},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["password"][0], "This field is required.")

        # Testing with invalid credentials
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "wrong", "password": "wrongpassword"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "No active account found with the given credentials",
        )

        # Testing with valid credentials
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": "user",
                "password": "bar",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("refresh" in response.data)
        self.assertTrue("access" in response.data)

    def test_auth_refresh(self):
        """Testing the refresh token API"""
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": "user",
                "password": "bar",
            },
        )
        refresh = response.data["refresh"]

        # Testing with missing fields
        response = self.client.post("/api/v1/auth/token/refresh/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["refresh"][0], "This field is required.")

        # Testing with wrong token
        response = self.client.post("/api/v1/auth/token/refresh/", {"refresh": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Token is invalid or expired",
        )

        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {
                "refresh": refresh,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("refresh" in response.data)
        self.assertTrue("access" in response.data)

    def test_auth_verify(self):
        """Testing the verify token API"""
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": "user",
                "password": "bar",
            },
        )
        access = response.data["access"]

        # Testing with missing fields
        response = self.client.post("/api/v1/auth/token/verify/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["token"][0], "This field is required.")

        # Testing with wrong token
        response = self.client.post("/api/v1/auth/token/verify/", {"token": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Token is invalid or expired",
        )

        response = self.client.post(
            "/api/v1/auth/token/verify/",
            {
                "token": access,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_forgot_password(self):
        """Testing the forgot password API"""

        # Testing with missing fields
        response = self.client.post("/api/v1/password_reset/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["username"][0], "This field is required.")

        # Testing with wrong data
        response = self.client.post(
            "/api/v1/password_reset/",
            {"username": "wrong"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing with inactive user
        user = self.create_user(username="test1", district=self.district)
        user.is_active = False
        user.save()
        response = self.client.post(
            "/api/v1/password_reset/",
            {"username": user.username},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        User.objects.filter(username="test1").delete()

        # Testing with valid data
        response = self.client.post(
            "/api/v1/password_reset/",
            {"username": self.user.username},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(ResetPasswordToken.objects.filter(user=self.user).exists())

    def test_verify_token(self):
        """Testing the verify password reset token API"""

        # Testing with missing fields
        response = self.client.post("/api/v1/password_reset/check/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "The password reset link is invalid")

        # Testing with wrong data
        response = self.client.post(
            "/api/v1/password_reset/check/",
            {"token": "wrongtoken", "email": "wrong@g.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "The password reset link is invalid")

        # Testing with other token
        user = self.create_user(username="test1", district=self.district)
        token = self.create_reset_password_token(user=user)
        response = self.client.post(
            "/api/v1/password_reset/check/",
            {"token": token.key, "email": self.user.email},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing with inactive user
        user.is_active = False
        user.save()
        response = self.client.post(
            "/api/v1/password_reset/check/",
            {"token": token.key, "email": user.email},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Testing with expired token
        token = self.create_reset_password_token(user=self.user, expired=True)
        response = self.client.post(
            "/api/v1/password_reset/check/",
            {"token": token.key, "email": self.user.email},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"],
            "The password reset link has expired",
        )
        ResetPasswordToken.objects.filter(user=self.user).delete()

        # Testing with valid token
        token = self.create_reset_password_token(user=self.user)
        response = self.client.post(
            "/api/v1/password_reset/check/",
            {"token": token.key, "email": self.user.email},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reset_password_with_token(self):
        """Testing the reset password API with token"""

        # Testing with missing fields
        response = self.client.post("/api/v1/password_reset/confirm/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["token"][0], "This field is required.")
        self.assertEqual(response.json()["password"][0], "This field is required.")

        # Testing with wrong data
        response = self.client.post(
            "/api/v1/password_reset/confirm/",
            {
                "token": "wrongtoken",
                "password": "test@123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Not found.")

        # Testing with other token
        user = self.create_user(username="test1", district=self.district)
        token = self.create_reset_password_token(user=user)
        response = self.client.post(
            "/api/auth/verify",
            {
                "token": token.key,
                "password": "test@123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Testing with inactive user
        user.is_active = False
        user.save()
        response = self.client.post(
            "/api/auth/verify",
            {
                "token": token.key,
                "password": "test@123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Testing with expired token
        token = self.create_reset_password_token(user=self.user, expired=True)
        response = self.client.post(
            "/api/v1/password_reset/confirm/",
            {
                "token": token.key,
                "password": "test@123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Not found.")
        ResetPasswordToken.objects.filter(user=self.user).delete()

        # Testing with valid token
        token = self.create_reset_password_token(user=self.user)
        response = self.client.post(
            "/api/v1/password_reset/confirm/",
            {
                "token": token.key,
                "password": "test@123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
