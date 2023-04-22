"""
Test cases for AssetLocationViewSet
"""
from rest_framework import status
from rest_framework.test import APITestCase

from care.users.models import User
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

    def get_detail_duty_staff_representation(self, obj=None) -> dict:
        """
        Returns duty staff representation
        """
        return {
            "id": obj.id,
            "username": obj.username,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "email": obj.email,
            "user_type": User.REVERSE_TYPE_MAP[obj.user_type],
        }

    def get_base_url(self, asset_id=None) -> str:
        """
        Returns base url for AssetLocationViewSet
        """
        if asset_id is not None:
            return f"/api/v1/facility/{self.facility.external_id}/asset_location/{asset_id}/"
        return f"/api/v1/facility/{self.facility.external_id}/asset_location/"

    def test_list_asset_locations(self):
        """
        Test list asset locations
        """
        res = self.client.get(self.get_base_url())
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, self.asset_location.external_id)

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

    def test_duty_staff_location(self):
        """
        Test duty staff location
        """

        # adding doctors
        doctor = self.create_user(
            username="doctor",
            district=self.district,
            local_body=self.local_body,
            home_facility=self.facility,
            user_type=15,
        )
        asset = self.create_asset_location(self.facility)
        asset.duty_staff.set([doctor])
        asset.save()
        res = self.client.get(self.get_base_url(asset.external_id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        duty_staff_objects = res.json()["duty_staff_objects"]
        self.assertEqual(len(duty_staff_objects), 1)
        self.assertDictContainsSubset(
            self.get_detail_duty_staff_representation(doctor), duty_staff_objects[0]
        )
