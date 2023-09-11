from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class AssetPublicViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)

    def test_retrieve_asset(self):
        response = self.client.get(f"/api/v1/public/asset/{self.asset.external_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_nonexistent_asset(self):
        response = self.client.get("/api/v1/public/asset/nonexistent/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
