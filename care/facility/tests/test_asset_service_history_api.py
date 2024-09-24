from datetime import timedelta

from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import AssetService
from care.facility.models.asset import AssetServiceEdit
from care.utils.tests.test_utils import TestUtils


class AssetServiceViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)
        cls.today = now().strftime("%Y-%m-%d")
        cls.yesterday = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
        cls.asset_service = AssetService.objects.create(
            asset=cls.asset,
            serviced_on=cls.today,
            note="Test Note",
        )
        cls.asset_service_initital_edit = AssetServiceEdit.objects.create(
            asset_service=cls.asset_service,
            serviced_on=cls.today,
            note="Test Note",
            edited_on=now(),
            edited_by=cls.user,
        )

    def test_list_asset_service(self):
        response = self.client.get(
            f"/api/v1/asset/{self.asset.external_id}/service_records/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_asset_service(self):
        response = self.client.get(
            f"/api/v1/asset/{self.asset.external_id}/service_records/{self.asset_service.external_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_asset_service_record(self):
        response = self.client.get(f"/api/v1/asset/{self.asset.external_id}/")
        self.assertEqual(response.data.get("last_service"), None)

        sample_data = {"last_serviced_on": self.today, "note": "Hello"}
        response = self.client.patch(
            f"/api/v1/asset/{self.asset.external_id}/", sample_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_service"]["serviced_on"], self.today)
        self.assertEqual(response.data["last_service"]["note"], "Hello")

    def test_update_asset_service_record(self):
        sample_data = {"last_serviced_on": self.today, "note": "Hello 2"}
        response = self.client.patch(
            f"/api/v1/asset/{self.asset.external_id}/", sample_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_service"]["serviced_on"], self.today)
        self.assertEqual(response.data["last_service"]["note"], "Hello 2")

    def test_edit_asset_service_record(self):
        sample_data = {"serviced_on": self.yesterday, "note": "Hello 3"}
        response = self.client.patch(
            f"/api/v1/asset/{self.asset.external_id}/service_records/{self.asset_service.external_id}/",
            sample_data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["serviced_on"], self.yesterday)
        self.assertEqual(response.data["note"], "Hello 3")
        self.assertEqual(len(response.data["edits"]), 2)
