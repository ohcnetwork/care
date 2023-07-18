from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.asset import AssetAvailabilityViewSet
from care.facility.models import Asset, AssetAvailabilityRecord, AssetLocation
from care.facility.models.asset import AvailabilityStatus
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class AssetAvailabilityViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        facility = self.create_facility(district=district, user=self.user)
        self.asset_from_location = AssetLocation.objects.create(
            name="asset from location", location_type=1, facility=facility
        )
        self.asset_to_location = AssetLocation.objects.create(
            name="asset to location", location_type=1, facility=facility
        )
        self.asset = Asset.objects.create(
            name="Test Asset", current_location=self.asset_from_location, asset_type=50
        )

        self.asset_availability = AssetAvailabilityRecord.objects.create(
            asset=self.asset,
            status=AvailabilityStatus.OPERATIONAL.value,
            timestamp=timezone.now(),
        )

    def test_list_asset_availability(self):
        response = self.new_request(
            ("/api/v1/asset_availability/",),
            {"get": "list"},
            AssetAvailabilityViewSet,
            True,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["status"], AvailabilityStatus.OPERATIONAL.value
        )

    def test_retrieve_asset_availability(self):
        response = self.new_request(
            (f"/api/v1/asset_availability/{self.asset_availability.id}/",),
            {"get": "retrieve"},
            AssetAvailabilityViewSet,
            True,
            {"pk": self.asset_availability.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AvailabilityStatus.OPERATIONAL.value)
