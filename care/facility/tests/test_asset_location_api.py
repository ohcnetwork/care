from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class AssetLocationViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

    def test_list_asset_locations(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset_location.external_id)

    def test_retrieve_asset_location(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location.external_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.asset_location.external_id))
        self.assertEqual(
            response.data["middleware_address"], self.asset_location.middleware_address
        )

    def test_create_asset_location(self):
        sample_data = {
            "name": "Test Asset Location",
            "middleware_address": "example.com",
        }
        response = self.client.post(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/",
            sample_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], sample_data["name"])
        self.assertEqual(
            response.data["middleware_address"], sample_data["middleware_address"]
        )

    def test_update_asset_location(self):
        sample_data = {
            "name": "Updated Test Asset Location",
            "middleware_address": "updated.example.com",
        }
        response = self.client.patch(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location.external_id}/",
            sample_data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_data["name"])
        self.assertEqual(
            response.data["middleware_address"], sample_data["middleware_address"]
        )

    def test_create_asset_location_invalid_middleware(self):
        sample_data = {
            "name": "Test Asset Location",
            "middleware_address": "https://invalid.middleware.///",
        }
        response = self.client.post(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/",
            sample_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["middleware_address"][0].code, "invalid_domain_name"
        )
