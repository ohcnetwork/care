from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import Bed
from care.utils.tests.test_utils import TestUtils


class SingleBedTest(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

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

    def test_create_with_same_name(self):
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

        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["name"],
            ["Bed with same name already exists in location."],
        )

        # validate case insensitive
        sample_data["name"] = "test bed"
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["name"],
            ["Bed with same name already exists in location."],
        )

        self.assertEqual(Bed.objects.filter(facility=self.facility).count(), 1)

    def test_create_with_name_previously_deleted(self):
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

        bed = Bed.objects.get(name="Test Bed")
        bed.deleted = True
        bed.save()

        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Bed.objects.filter(facility=self.facility).count(), 1)


class MultipleBedTest(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset = cls.create_asset(cls.asset_location)
        cls.user = cls.create_user(
            "distadmin", cls.district, home_facility=cls.facility, user_type=30
        )

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

    def test_create_with_duplicate_name(self):
        sample_data = {
            "bed_type": "REGULAR",
            "description": "Testing creation of beds.",
            "facility": self.facility.external_id,
            "location": self.asset_location.external_id,
            "name": "Test",
            "number_of_beds": 5,
        }
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Bed with same name already exists in this location.",
        )

        # validate case insensitive
        sample_data["name"] = "test"
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Bed with same name already exists in this location.",
        )

        self.assertEqual(Bed.objects.filter(facility=self.facility).count(), 5)
