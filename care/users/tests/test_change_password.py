from django.urls import reverse
from rest_framework import status

from care.utils.tests.base import CareAPITestBase


class UserChangePasswordTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user_with_password(
            username="testuser", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("change_password_view")
        self.payload = {"old_password": "password123", "new_password": "newpassword456"}

    def test_change_password_success(self):
        response = self.client.put(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Password updated successfully")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword456"))

    def test_change_password_wrong_old_password(self):
        self.payload["old_password"] = "wrongpassword"
        response = self.client.put(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["errors"][0]["msg"],
            "Value error, Wrong password entered. Please check your password.",
        )

    def test_change_password_weak_new_password(self):
        self.payload["new_password"] = "123"
        response = self.client.put(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(
            response,
            "This password is too short",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_change_password_invalid_password(self):
        self.payload["new_password"] = "password123"
        response = self.client.put(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("password123"))

    def test_change_password_with_leading_whitespace(self):
        """
        Test that password with leading whitespace is handled consistently.
        The password should be stripped before validation, matching login behavior.
        """
        self.payload["old_password"] = f"  {self.payload['old_password']}"
        response = self.client.put(
            self.url,
            self.payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Password updated successfully"})

    def test_change_password_with_trailing_whitespace(self):
        """
        Test that password with trailing whitespace is handled consistently.
        The password should be stripped before validation, matching login behavior.
        """
        self.payload["old_password"] = f"{self.payload['old_password']}  "
        response = self.client.put(
            self.url,
            self.payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Password updated successfully"})

    def test_change_password_with_leading_and_trailing_whitespace(self):
        """
        Test that password with both leading and trailing whitespace is handled consistently.
        The password should be stripped before validation, matching login behavior.
        """
        self.payload["old_password"] = f"  {self.payload['old_password']}  "
        response = self.client.put(
            self.url,
            self.payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Password updated successfully"})
