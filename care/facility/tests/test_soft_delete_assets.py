from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class SoftDeleteAssets(APITestCase, TestUtils):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

    def setUp(self) -> None:
        super().setUp()
        self.asset = self.create_asset(self.asset_location)

    def test_asset_soft_delete_api(self):
        self.client.delete(f"api/v1/facility/{self.facility.external_id}")
        response = self.client.get(f"api/v1/asset?facility={self.facility.external_id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
