from rest_framework import status

from care.facility.models import AssetLocation, Bed
from care.utils.tests.test_base import TestBase


class SingleBedTest(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self.asset_location: AssetLocation = AssetLocation.objects.create(
            name="asset location", location_type=1, facility=self.facility
        )

    def tearDown(self) -> None:
        Bed._default_manager.filter(facility=self.facility).delete()
        AssetLocation._default_manager.filter(id=self.asset_location.id).delete()

    def test_create(self):
        sample_data = {
            "bed_type": "REGULAR",
            "description": "Testing creation of beds.",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
            "name": "Test Bed",
            "number_of_beds": 1,
        }
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Bed.objects.filter(facility=self.facility).count(),
            sample_data["number_of_beds"],
        )


class MultipleBedTest(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self.asset_location: AssetLocation = AssetLocation.objects.create(
            name="asset location", location_type=1, facility=self.facility
        )

    def tearDown(self) -> None:
        Bed._default_manager.filter(facility=self.facility).delete()
        AssetLocation._default_manager.filter(id=self.asset_location.id).delete()

    def test_create(self):
        sample_data = {
            "bed_type": "REGULAR",
            "description": "Testing creation of beds.",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
            "name": "Test Bed",
            "number_of_beds": 5,
        }
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Bed.objects.filter(facility=self.facility).count(),
            sample_data["number_of_beds"],
        )

    def test_create_with_more_than_allowed_value(self):
        sample_data = {
            "bed_type": "REGULAR",
            "description": "Testing creation of beds.",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
            "name": "Test 2 Bed",
            "number_of_beds": 101,
        }
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Bed.objects.filter(facility=self.facility).count(), 0)
