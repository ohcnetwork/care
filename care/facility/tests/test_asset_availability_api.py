from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import AssetAvailabilityRecord
from care.facility.models.asset import AvailabilityStatus
from care.utils.tests.test_utils import TestUtils


class AssetAvailabilityViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.asset_availability = AssetAvailabilityRecord.objects.create(
            asset=cls.asset,
            status=AvailabilityStatus.OPERATIONAL.value,
            timestamp=timezone.now(),
        )

    def test_list_asset_availability(self):
        response = self.client.get("/api/v1/asset_availability/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["status"], AvailabilityStatus.OPERATIONAL.value
        )

    def test_retrieve_asset_availability(self):
        response = self.client.get(
            f"/api/v1/asset_availability/{self.asset_availability.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AvailabilityStatus.OPERATIONAL.value)
