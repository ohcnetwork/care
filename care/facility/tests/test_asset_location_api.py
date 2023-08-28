from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetLocationViewSet
from care.facility.models import AssetLocation
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetLocationViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        self.facility = self.create_facility(district=district, user=self.user)
        self.asset_location = AssetLocation.objects.create(
            name="asset location", location_type=1, facility=self.facility
        )

    def test_list_asset_locations(self):
        response = self.new_request(
            (f"/api/v1/asset_location/{self.facility.external_id}",),
            {"get": "list"},
            AssetLocationViewSet,
            self.user,
            {"facility_external_id": self.facility.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset_location.external_id)

    def test_retrieve_asset_location(self):
        response = self.new_request(
            (f"/api/v1/asset_location/{self.facility.external_id}/",),
            {"get": "retrieve"},
            AssetLocationViewSet,
            self.user,
            {
                "facility_external_id": self.facility.external_id,
                "external_id": self.asset_location.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset_location.external_id)

    def test_create_asset_location(self):
        sample_data = {"name": "Test Asset Location"}
        response = self.new_request(
            (
                "/api/v1/asset-location/{self.facility.external_id}/",
                sample_data,
                "json",
            ),
            {"post": "create"},
            AssetLocationViewSet,
            self.user,
            {"facility_external_id": self.facility.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_asset_location(self):
        sample_data = {"name": "Updated Test Asset Location"}
        response = self.new_request(
            (
                "/api/v1/asset-location/{self.facility.external_id}/",
                sample_data,
                "json",
            ),
            {"patch": "partial_update"},
            AssetLocationViewSet,
            self.user,
            {
                "facility_external_id": self.facility.external_id,
                "external_id": self.asset_location.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_data["name"])
