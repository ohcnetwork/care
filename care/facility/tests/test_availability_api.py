from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import AvailabilityRecord
from care.facility.models.asset import Asset, AssetLocation, AvailabilityStatus
from care.utils.tests.test_utils import TestUtils


class AvailabilityViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        asset_content_type = ContentType.objects.get_for_model(Asset)
        location_content_type = ContentType.objects.get_for_model(AssetLocation)
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.asset_availability = AvailabilityRecord.objects.create(
            content_type=asset_content_type,
            object_external_id=cls.asset.external_id,
            status=AvailabilityStatus.OPERATIONAL.value,
            timestamp=timezone.now(),
        )
        cls.location_availability = AvailabilityRecord.objects.create(
            content_type=location_content_type,
            object_external_id=cls.asset_location.external_id,
            status=AvailabilityStatus.OPERATIONAL.value,
            timestamp=timezone.now(),
        )

    def test_list_asset_availability(self):
        response = self.client.get(
            f"/api/v1/asset/{self.asset.external_id}/availability/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["status"], AvailabilityStatus.OPERATIONAL.value
        )

    def test_list_location_availability(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location.external_id}/availability/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["status"], AvailabilityStatus.OPERATIONAL.value
        )

    def test_no_access_to_availability_record(self):
        user2 = self.create_user(username="user2", district=self.district)
        self.client.force_authenticate(user2)
        response = self.client.get(
            f"/api/v1/asset/{self.asset.external_id}/availability/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "You do not have access to this asset's availability records",
        )
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/asset_location/{self.asset_location.external_id}/availability/"
        )
        self.assertEqual(
            response.data["detail"],
            "You do not have access to this asset location's availability records",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
