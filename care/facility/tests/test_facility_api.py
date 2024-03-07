from rest_framework import status
from rest_framework.test import APITestCase

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
        sample_data = {
            "name": "Hospital X",
            "district": self.district.pk,
            "state": self.state.pk,
            "local_body": self.local_body.pk,
            "facility_type": "Educational Inst",
            "address": "Nearby",
            "pincode": 390024,
            "features": [],
        }
        self.client.force_authenticate(user=dist_admin)
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
