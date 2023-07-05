from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetPublicViewSet
from care.facility.models import Asset, AssetLocation
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetPublicViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        facility = self.create_facility(district=district, user=self.user)
        self.asset_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=facility
        )
        self.asset = Asset.objects.create(
            name="Test Asset", current_location=self.asset_location, asset_type=50
        )

    def test_retrieve_asset(self):
        response = self.new_request(
            (f"/api/v1/public/asset/{self.asset.external_id}/",),
            {"get": "retrieve"},
            AssetPublicViewSet,
            self.user,
            {"external_id": str(self.asset.external_id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_cached_asset(self):
        key = "asset:" + str(self.asset.external_id)
        cache.set(key, {"name": "Cached Asset"}, 60 * 60 * 24)

        response = self.new_request(
            (f"/api/v1/public/asset/{self.asset.external_id}/",),
            {"get": "retrieve"},
            AssetPublicViewSet,
            self.user,
            {"external_id": str(self.asset.external_id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Cached Asset")

    def test_retrieve_nonexistent_asset(self):
        response = self.new_request(
            ("/api/v1/public/asset/nonexistent/",),
            {"get": "retrieve"},
            AssetPublicViewSet,
            self.user,
            {"external_id": "nonexistent"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
