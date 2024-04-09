import json
from unittest.mock import patch

from authlib.jose import JsonWebKey
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.utils.jwks.token_generator import generate_jwt
from care.utils.tests.test_utils import TestUtils

factory = APIRequestFactory()


class MiddlewareAuthTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(
            cls.super_user,
            cls.district,
            cls.local_body,
            middleware_address="test-middleware.net",
        )
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)

    def setUp(self) -> None:
        self.private_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        self.public_key = json.dumps(self.private_key.as_dict())

    def test_middleware_asset_authentication_unsuccessful(self):
        response = self.client.get("/middleware/verify-asset")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("config.authentication.MiddlewareAuthentication.get_public_key")
    def test_middleware_asset_authentication_successful(self, mock_get_public_key):
        mock_get_public_key.return_value = self.public_key
        token = generate_jwt(
            claims={"asset_id": str(self.asset.external_id)},
            jwks=self.private_key,
        )

        response = self.client.get(
            "/middleware/verify-asset",
            headers={
                "Authorization": f"Middleware_Bearer {token}",
                "X-Facility-Id": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["username"], "asset" + str(self.asset.external_id)
        )

    def test_middleware_authentication_unsuccessful(self):
        response = self.client.get("/middleware/verify")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("config.authentication.MiddlewareAuthentication.get_public_key")
    def test_middleware_authentication_successful(self, mock_get_public_key):
        mock_get_public_key.return_value = self.public_key
        token = generate_jwt(jwks=self.private_key)

        response = self.client.get(
            "/middleware/verify",
            headers={
                "Authorization": f"Middleware_Bearer {token}",
                "X-Facility-Id": self.facility.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["username"], "middleware" + str(self.facility.external_id)
        )
