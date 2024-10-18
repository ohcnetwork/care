from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import AssetBed, Bed
from care.users.models import User
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.tests.test_utils import TestUtils


class BedViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.facility2 = cls.create_facility(
            cls.super_user, cls.district, cls.local_body
        )
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.asset_location2 = cls.create_asset_location(cls.facility2)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.bed1 = Bed.objects.create(
            name="bed1", location=cls.asset_location, facility=cls.facility
        )
        cls.bed2 = Bed.objects.create(
            name="bed2", location=cls.asset_location, facility=cls.facility, bed_type=1
        )
        cls.bed3 = Bed.objects.create(
            name="bed3", location=cls.asset_location2, facility=cls.facility2
        )

    def test_list_beds(self):
        with self.assertNumQueries(5):
            response = self.client.get("/api/v1/bed/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # test list beds accessible to user
        response = self.client.get("/api/v1/bed/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

        self.client.force_login(self.super_user)

        # test list beds accessible to superuser (all beds)
        response = self.client.get("/api/v1/bed/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

        response = self.client.get("/api/v1/bed/", {"bed_type": "ISOLATION"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.bed2.name)
        self.assertEqual(response.data["count"], 1)

        response = self.client.get(
            "/api/v1/bed/",
            {"facility": self.facility2.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.bed3.name)
        self.assertEqual(response.data["count"], 1)

        response = self.client.get(
            "/api/v1/bed/",
            {"location": self.asset_location2.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], self.bed3.name)

        self.client.logout()

    def test_create_beds(self):
        base_data = {
            "name": "Sample Beds",
            "bed_type": 2,
            "location": self.asset_location.external_id,
            "facility": self.facility.external_id,
            "number_of_beds": 10,
            "description": "This is a sample bed description",
        }
        sample_data = base_data.copy()  # Create a fresh copy of the base data
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bed.objects.filter(bed_type=2).count(), 10)

        # without location
        sample_data = base_data.copy()
        sample_data.update({"location": None})
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["location"][0], "This field may not be null.")

        # without facility
        sample_data = base_data.copy()
        sample_data.update({"facility": None})
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["facility"][0], "This field may not be null.")

        # Test - if beds > 100
        sample_data = base_data.copy()
        sample_data.update({"number_of_beds": 200})
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["number_of_beds"][0],
            "Cannot create more than 100 beds at once.",
        )

        # creating bed in different facility
        sample_data = base_data.copy()
        sample_data.update(
            {
                "location": self.asset_location2.external_id,
                "facility": self.facility2.external_id,
            }
        )
        response = self.client.post("/api/v1/bed/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_bed(self):
        response = self.client.get(f"/api/v1/bed/{self.bed1.external_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "bed1")

    def test_update_bed(self):
        updated_data = {
            "name": "Updated Bed Name",
            "bed_type": 3,
            "location": self.asset_location.external_id,
            "facility": self.facility.external_id,
        }
        response = self.client.put(
            f"/api/v1/bed/{self.bed2.external_id}/", updated_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bed2.refresh_from_db()
        self.assertEqual(self.bed2.name, updated_data["name"])
        self.assertEqual(self.bed2.bed_type, updated_data["bed_type"])

    def test_patch_update_bed(self):
        self.client.force_login(self.super_user)

        # we always need to send location and facility since serializer is written that way
        partial_data = {
            "description": "Updated Bed Description",
            "location": self.asset_location.external_id,
            "facility": self.facility.external_id,
        }
        response = self.client.patch(
            f"/api/v1/bed/{self.bed3.external_id}/", partial_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bed3.refresh_from_db()
        self.assertEqual(self.bed3.description, partial_data["description"])
        self.client.logout()

    def test_delete_bed_without_permission(self):
        response = self.client.delete(f"/api/v1/bed/{self.bed1.external_id}/")
        self.assertFalse(self.user.user_type == User.TYPE_VALUE_MAP["DistrictLabAdmin"])
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Bed.objects.filter(id=self.bed1.id).exists())

    def test_delete_bed(self):
        user2 = self.create_user(
            "Sample User",
            self.district,
            home_facility=self.facility,
            user_type=User.TYPE_VALUE_MAP["DistrictLabAdmin"],
        )
        self.client.force_login(user2)
        self.assertTrue(user2.user_type == User.TYPE_VALUE_MAP["DistrictLabAdmin"])
        response = self.client.delete(f"/api/v1/bed/{self.bed1.external_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Bed.objects.filter(id=self.bed1.id).exists())

    def test_list_non_occupied_beds(self):
        linked_bed = Bed.objects.create(
            name="linked_bed",
            location=self.asset_location,
            facility=self.facility,
        )
        asset = self.create_asset(
            self.asset_location, asset_class=AssetClasses.HL7MONITOR.name
        )
        AssetBed.objects.create(bed=linked_bed, asset=asset)

        # 3 beds 1 linked with HL7MONITOR and 2 created in setup [with same facility]

        response = self.client.get("/api/v1/bed/")

        # Assert list returns 3 beds
        self.assertEqual(response.json()["count"], 3)

        response_with_not_occupied_bed = self.client.get(
            "/api/v1/bed/",
            {"not_occupied_by_asset_type": "HL7MONITOR"},
        )

        # Assert count of unoccupied beds is 2 (3 in total , 1 occupied)
        self.assertEqual(response_with_not_occupied_bed.json()["count"], 2)
