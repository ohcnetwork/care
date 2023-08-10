from datetime import datetime

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetServiceViewSet, AssetViewSet
from care.facility.models import Asset, AssetLocation, AssetService
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetServiceViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.today = datetime.today().strftime("%Y-%m-%d")
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        facility = self.create_facility(district=district, user=self.user)
        self.asset_location = AssetLocation.objects.create(
            name="asset from location", location_type=1, facility=facility
        )
        self.asset = Asset.objects.create(
            name="Test Asset", current_location=self.asset_location, asset_type=50
        )
        self.asset_service = AssetService.objects.create(
            asset=self.asset,
            serviced_on=self.today,
            note="Test Note",
        )

    def test_list_asset_service(self):
        response = self.new_request(
            ("/api/v1/asset_service/",),
            {"get": "list"},
            AssetServiceViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_asset_service(self):
        response = self.new_request(
            (f"/api/v1/asset_service/{self.asset_service.id}/",),
            {"get": "retrieve"},
            AssetServiceViewSet,
            self.user,
            {"pk": self.asset_service.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_asset_service_record(self):
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}",),
            {"get": "retrieve"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.data["last_service"], None)

        sample_data = {"last_serviced_on": self.today, "note": "Hello"}
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_service"]["serviced_on"], self.today)
        self.assertEqual(response.data["last_service"]["note"], "Hello")

    def test_update_asset_service_record(self):
        sample_data = {"last_serviced_on": self.today, "note": "Hello 2"}
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_service"]["serviced_on"], self.today)
        self.assertEqual(response.data["last_service"]["note"], "Hello 2")
