from care.utils.tests.test_base import TestBase
from rest_framework import status
from care.facility.api.viewsets.bed import BedViewSet
from care.facility.models import AssetLocation
from care.facility.tests.mixins import TestClassMixin
from rest_framework.test import APIRequestFactory, APITestCase

class SingleBedTest(TestBase, TestClassMixin, APITestCase):

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
            "number_of_beds": 1,
        }
        response = self.new_request(
            ("/api/v1/bed/", sample_data, "json"),
            {"post": "create"},
            BedViewSet,
            user
        )
        self.assertIs(response.status_code, status.HTTP_201_CREATED)

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
            ("/api/v1/bed/", sample_data, "json"),
            {"post": "create"},
            BedViewSet,
            user
        )
        self.assertIs(response.status_code, status.HTTP_201_CREATED)