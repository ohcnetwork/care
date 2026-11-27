from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from care.emr.api.viewsets.user import UserViewSet
from care.users.models import User


class UserDegreesAPITest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.url = reverse("users-degrees")
        self.view = UserViewSet.as_view({"get": "degrees"})
        self.user = User(username="degrees-user")

    def get_degrees(self, *, authenticated=True):
        request = self.factory.get(self.url)
        if authenticated:
            force_authenticate(request, user=self.user)
        return self.view(request)

    def test_returns_default_degrees_for_authenticated_user(self):
        response = self.get_degrees()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, settings.USER_QUALIFICATION_DEGREES)
        self.assertTrue(response.data)
        for degree in response.data:
            self.assertTrue(degree["code"])
            self.assertTrue(degree["system"])
            self.assertTrue(degree["display"])

    @override_settings(
        USER_QUALIFICATION_DEGREES=[
            {
                "code": "custom",
                "system": "https://example.org/degrees",
                "display": "Custom",
            }
        ]
    )
    def test_returns_configured_catalogue_without_pagination(self):
        response = self.get_degrees()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            [
                {
                    "code": "custom",
                    "system": "https://example.org/degrees",
                    "display": "Custom",
                }
            ],
        )

    @override_settings(USER_QUALIFICATION_DEGREES=[])
    def test_allows_empty_catalogue(self):
        response = self.get_degrees()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_requires_authentication(self):
        response = self.get_degrees(authenticated=False)

        self.assertIn(response.status_code, [401, 403])
