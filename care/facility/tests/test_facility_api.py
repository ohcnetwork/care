import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models.facility import FacilityHubSpoke
from care.utils.tests.test_utils import TestUtils


class FacilityTests(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.user = cls.create_user("staff", cls.district)

    def test_all_listing(self):
        response = self.client.get("/api/v1/getallfacilities/")
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_listing(self):
        response = self.client.get("/api/v1/facility/")
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        dist_admin = self.create_user("dist_admin", self.district, user_type=30)
        self.client.force_authenticate(user=dist_admin)

        sample_data_with_empty_feature_list = {
            "name": "Hospital X",
            "district": self.district.pk,
            "state": self.state.pk,
            "local_body": self.local_body.pk,
            "facility_type": "Educational Inst",
            "address": "Nearby",
            "pincode": 390024,
            "features": [],
        }
        response = self.client.post(
            "/api/v1/facility/", sample_data_with_empty_feature_list
        )
        self.assertIs(response.status_code, status.HTTP_201_CREATED)

        sample_data_with_invalid_choice = {
            "name": "Hospital X",
            "district": self.district.pk,
            "state": self.state.pk,
            "local_body": self.local_body.pk,
            "facility_type": "Educational Inst",
            "address": "Nearby",
            "pincode": 390024,
            "features": [1020, 2, 4, 5],
        }
        response = self.client.post(
            "/api/v1/facility/", sample_data_with_invalid_choice
        )

        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["features"][0][0].code, "invalid_choice")
        self.assertEqual(
            response.data["features"][0][0], '"1020" is not a valid choice.'
        )

        sample_data_with_duplicate_choices = {
            "name": "Hospital X",
            "district": self.district.pk,
            "state": self.state.pk,
            "local_body": self.local_body.pk,
            "facility_type": "Educational Inst",
            "address": "Nearby",
            "pincode": 390024,
            "features": [1, 1],
        }
        response = self.client.post(
            "/api/v1/facility/", sample_data_with_duplicate_choices
        )

        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["features"][0],
            "Features should not contain duplicate values.",
        )

        sample_data = {
            "name": "Hospital X",
            "district": self.district.pk,
            "state": self.state.pk,
            "local_body": self.local_body.pk,
            "facility_type": "Educational Inst",
            "address": "Nearby",
            "pincode": 390024,
            "features": [1, 2],
        }
        response = self.client.post("/api/v1/facility/", sample_data)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        fac_id = response.data["id"]
        retrieve_response = self.client.get(f"/api/v1/facility/{fac_id}/")
        self.assertIs(retrieve_response.status_code, status.HTTP_200_OK)

    def test_no_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/facility/")
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

        sample_data = {}
        create_response = self.client.post("/api/v1/facility/", sample_data)
        self.assertIs(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete(self):
        state_admin = self.create_user("state_admin", self.district, user_type=40)
        district2 = self.create_district(self.state)
        facility = self.create_facility(self.super_user, district2, self.local_body)
        self.client.force_authenticate(user=state_admin)
        response = self.client.delete(f"/api/v1/facility/{facility.external_id}/")
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        dist_admin = self.create_user("dist_admin", self.district, user_type=30)
        facility = self.create_facility(self.super_user, self.district, self.local_body)
        self.client.force_authenticate(user=dist_admin)
        response = self.client.delete(f"/api/v1/facility/{facility.external_id}/")
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_no_permission(self):
        facility = self.create_facility(self.super_user, self.district, self.local_body)

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/v1/facility/{facility.external_id}/")
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

        state2 = self.create_state()
        district2 = self.create_district(state2)

        state_admin = self.create_user("state_admin", district2, user_type=40)
        self.client.force_authenticate(user=state_admin)
        response = self.client.delete(f"/api/v1/facility/{facility.external_id}/")
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        dist_admin = self.create_user("dist_admin", district2, user_type=30)
        self.client.force_authenticate(user=dist_admin)
        response = self.client.delete(f"/api/v1/facility/{facility.external_id}/")
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_with_active_patients(self):
        facility = self.create_facility(self.super_user, self.district, self.local_body)
        self.create_patient(self.district, facility)

        state_admin = self.create_user("state_admin", self.district, user_type=40)
        self.client.force_authenticate(user=state_admin)
        response = self.client.delete(f"/api/v1/facility/{facility.external_id}/")
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_spoke(self):
        facility = self.create_facility(self.super_user, self.district, self.local_body)
        facility2 = self.create_facility(
            self.super_user, self.district, self.local_body
        )

        state_admin = self.create_user("state_admin", self.district, user_type=40)
        self.client.force_authenticate(user=state_admin)
        response = self.client.post(
            f"/api/v1/facility/{facility.external_id}/spokes/",
            {"spoke": facility2.external_id},
        )
        self.assertIs(response.status_code, status.HTTP_201_CREATED)

    def test_delete_spoke(self):
        facility = self.create_facility(self.super_user, self.district, self.local_body)
        facility2 = self.create_facility(
            self.super_user, self.district, self.local_body
        )

        state_admin = self.create_user("state_admin", self.district, user_type=40)

        spoke = FacilityHubSpoke.objects.create(hub=facility, spoke=facility2)
        self.client.force_authenticate(user=state_admin)
        response = self.client.delete(
            f"/api/v1/facility/{facility.external_id}/spokes/{spoke.external_id}/"
        )
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_add_spoke_no_permission(self):
        facility = self.create_facility(self.super_user, self.district, self.local_body)
        facility2 = self.create_facility(
            self.super_user, self.district, self.local_body
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/v1/facility/{facility.external_id}/spokes/",
            {"spoke": facility2.external_id},
        )
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_spoke_no_permission(self):
        facility = self.create_facility(self.super_user, self.district, self.local_body)
        facility2 = self.create_facility(
            self.super_user, self.district, self.local_body
        )

        spoke = FacilityHubSpoke.objects.create(hub=facility, spoke=facility2)
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f"/api/v1/facility/{facility.external_id}/spokes/{spoke.external_id}/"
        )
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_spoke_is_not_ancestor(self):
        facility_a = self.create_facility(
            self.super_user, self.district, self.local_body
        )
        facility_b = self.create_facility(
            self.super_user, self.district, self.local_body
        )
        facility_c = self.create_facility(
            self.super_user, self.district, self.local_body
        )

        FacilityHubSpoke.objects.create(hub=facility_a, spoke=facility_b)
        FacilityHubSpoke.objects.create(hub=facility_b, spoke=facility_c)

        self.client.force_authenticate(user=self.super_user)
        response = self.client.post(
            f"/api/v1/facility/{facility_c.external_id}/spokes/",
            {"spoke": facility_a.external_id},
        )
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hubs_list(self):
        facility_a = self.create_facility(
            self.super_user, self.district, self.local_body
        )
        facility_b = self.create_facility(
            self.super_user, self.district, self.local_body
        )

        FacilityHubSpoke.objects.create(hub=facility_a, spoke=facility_b)

        self.client.force_authenticate(user=self.super_user)
        response = self.client.get(f"/api/v1/facility/{facility_b.external_id}/hubs/")
        self.assertIs(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["results"][0]["hub_object"]["id"], str(facility_a.external_id)
        )


class FacilityCoverImageTests(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

    def test_valid_image(self):
        self.facility.cover_image = "http://example.com/test.jpg"
        self.facility.save()
        image = Image.new("RGB", (400, 400))
        file = io.BytesIO()
        image.save(file, format="JPEG")
        test_file = SimpleUploadedFile("test.jpg", file.getvalue(), "image/jpeg")
        test_file.size = 2048

        payload = {"cover_image": test_file}

        response = self.client.post(
            f"/api/v1/facility/{self.facility.external_id}/cover_image/",
            payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_image_too_small(self):
        image = Image.new("RGB", (100, 100))
        file = io.BytesIO()
        image.save(file, format="JPEG")
        test_file = SimpleUploadedFile("test.jpg", file.getvalue(), "image/jpeg")
        test_file.size = 1000

        payload = {"cover_image": test_file}

        response = self.client.post(
            f"/api/v1/facility/{self.facility.external_id}/cover_image/",
            payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["cover_image"][0],
            "Image width is less than the minimum allowed width of 400 pixels.",
        )
