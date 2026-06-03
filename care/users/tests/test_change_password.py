from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class TestChangePassword(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="vipul",
            password="StrongPass@123",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("change_password_view")

    def test_weak_password_is_rejected(self):
        """Test that passwords failing Django's built-in validation are rejected."""
        payload = {
            "old_password": "StrongPass@123",
            "new_password": "123",  # Too short for Django's default (8 chars)
        }
        response = self.client.put(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that 'new_password' is in the error response keys
        self.assertIn("new_password", response.data)

    def test_wrong_old_password_fails(self):
        """Ensure the user must provide the correct current password."""
        payload = {
            "old_password": "WrongCurrentPassword",
            "new_password": "NewStrongPass@456",
        }
        response = self.client.put(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)

    def test_password_change_success(self):
        """Test that a valid password change works correctly."""
        payload = {
            "old_password": "StrongPass@123",
            "new_password": "NewStrongPass@456",
        }
        response = self.client.put(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the password actually changed in the DB
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass@456"))
