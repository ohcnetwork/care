from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedListNotitificationKeys(Enum):
    id = "id"
    event = "event"
    caused_by = "caused_by"
    message = "message"
    created_date = "created_date"
    read_at = "read_at"


class ExpectedListCausedByKeys(Enum):
    id = "id"
    first_name = "first_name"
    last_name = "last_name"
    user_type = "user_type"
    username = "username"
    email = "email"
    last_login = "last_login"


class ExpectedRetrieveNotificationKeys(Enum):
    id = "id"
    event = "event"
    caused_by = "caused_by"
    event_type = "event_type"
    created_date = "created_date"
    read_at = "read_at"
    message = "message"
    caused_objects = "caused_objects"


class ExpectedRetrieveCausedByKeys(Enum):
    id = "id"
    first_name = "first_name"
    username = "username"
    email = "email"
    last_name = "last_name"
    user_type = "user_type"
    last_login = "last_login"


class NotificationViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        cls.notification = cls.create_notification()

    def setUp(self) -> None:
        # Refresh token to header
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_notifications(self):
        response = self.client.get("/api/v1/notification/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedListNotitificationKeys]

        data = response.json()["results"][0]

        self.assertCountEqual(data.keys(), expected_keys)

        caused_by_keys = [key.value for key in ExpectedListCausedByKeys]
        self.assertCountEqual(data["caused_by"].keys(), caused_by_keys)

    def test_retrieve_notification(self):
        response = self.client.get(
            f"/api/v1/notification/{self.notification.external_id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedRetrieveNotificationKeys]

        data = response.json()

        self.assertCountEqual(data.keys(), expected_keys)

        caused_by_keys = [key.value for key in ExpectedRetrieveCausedByKeys]
        self.assertCountEqual(data["caused_by"].keys(), caused_by_keys)

    def test_public_key(self):
        response = self.client.get("/api/v1/notification/public_key/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = ["public_key"]

        data = response.json()

        self.assertCountEqual(data.keys(), expected_keys)

    def test_notify(self):
        data = {"facility": self.facility.external_id, "message": "Test Message"}
        response = self.client.post("/api/v1/notification/notify/", data=data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_notify_missing_facility_message(self):
        data = {
            "facility": self.facility.external_id,
        }
        response = self.client.post("/api/v1/notification/notify/", data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(response.json()["message"], "is required")

        data = {"message": "Test Message"}
        response = self.client.post("/api/v1/notification/notify/", data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["facility"], "is required")
