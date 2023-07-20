from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.bed import BedViewSet
from care.facility.models import AssetLocation, Bed
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class SingleBedTest(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = APIRequestFactory()
        state = cls.create_state()
        district = cls.create_district(state=state)
        cls.user = cls.create_user(district=district, username="test user")
        cls.facility = cls.create_facility(district=district, user=cls.user)
        cls.asset_location: AssetLocation = AssetLocation.objects.create(
            name="asset location", location_type=1, facility=cls.facility
        )

    def tearDown(self) -> None:
        Bed._default_manager.filter(facility=self.facility).delete()

    @classmethod
    def tearDownClass(cls):
        cls.facility.delete()
        cls.user.delete()
        cls.asset_location.delete()

    def test_create(self):
        user = self.user
        sample_data = {
            "bed_type": "REGULAR",
            "description": "Testing creation of beds.",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
            "name": "Test Bed",
            "number_of_beds": 1,
        }
        response = self.new_request(
            ("/api/v1/bed/", sample_data, "json"), {"post": "create"}, BedViewSet, user
        )
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Bed.objects.filter(facility=self.facility).count(),
            sample_data["number_of_beds"],
        )


class MultipleBedTest(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        state = self.create_state()
        district = self.create_district(state=state)
        self.user = self.create_user(district=district, username="test user")
        self.facility = self.create_facility(district=district, user=self.user)
        self.asset_location = AssetLocation.objects.create(
            name="asset location", location_type=1, facility=self.facility
        )

    def test_create(self):
        user = self.user
        sample_data = {
            "bed_type": "REGULAR",
            "description": "Testing creation of beds.",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
            "name": "Test Bed",
            "number_of_beds": 5,
        }
        response = self.new_request(
            ("/api/v1/bed/", sample_data, "json"), {"post": "create"}, BedViewSet, user
        )
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Bed.objects.filter(facility=self.facility).count(),
            sample_data["number_of_beds"],
        )
