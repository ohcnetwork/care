from datetime import datetime, timedelta

from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetServiceViewSet, AssetViewSet
from care.facility.models import Asset, AssetLocation, AssetService
from care.facility.models.asset import AssetServiceEdit
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetServiceViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.today = datetime.today().strftime("%Y-%m-%d")
        self.yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
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
        self.asset_service_initital_edit = AssetServiceEdit.objects.create(
            asset_service=self.asset_service,
            serviced_on=self.today,
            note="Test Note",
            edited_on=now(),
            edited_by=self.user,
        )

    def test_list_asset_service(self):
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}/service_records/",),
            {"get": "list"},
            AssetServiceViewSet,
            self.user,
            {"asset_external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_asset_service(self):
        response = self.new_request(
            (
                f"/api/v1/asset/{self.asset.external_id}/service_records/{self.asset_service.id}/",
            ),
            {"get": "retrieve"},
            AssetServiceViewSet,
            self.user,
            {
                "external_id": self.asset_service.external_id,
                "asset_external_id": self.asset.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_asset_service_record(self):
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}",),
            {"get": "retrieve"},
            AssetViewSet,
            self.user,
            {
                "external_id": self.asset.external_id,
            },
        )
        self.assertEqual(response.data["last_service"], None)

        sample_data = {"last_serviced_on": self.today, "note": "Hello"}
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {
                "external_id": self.asset.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_asset_service_record(self):
        sample_data = {"last_serviced_on": self.today, "note": "Hello 2"}
        response = self.new_request(
            (f"/api/v1/asset/{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {
                "external_id": self.asset.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_edit_asset_service_record(self):
        sample_data = {"serviced_on": self.yesterday, "note": "Hello 3"}
        response = self.new_request(
            (
                f"/api/v1/asset/{self.asset.external_id}/service_records/{self.asset_service.external_id}",
                sample_data,
                "json",
            ),
            {"patch": "partial_update"},
            AssetServiceViewSet,
            self.user,
            {
                "external_id": self.asset_service.external_id,
                "asset_external_id": self.asset.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["serviced_on"], self.yesterday)
        self.assertEqual(response.data["note"], "Hello 3")
        self.assertEqual(len(response.data["edits"]), 2)
