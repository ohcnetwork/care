from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class UnlinkDistrictAdmin(TestUtils, APITestCase):
    def setUp(self):
        settings.DISABLE_RATELIMIT = True
        self.state = self.create_state()

        self.district1 = self.create_district(self.state)
        self.admin1 = self.create_user("user12345678", self.district1, user_type=30)

        self.district2 = self.create_district(self.state)
        self.admin2 = self.create_user("user12345679", self.district2, user_type=30)

        self.local_body1 = self.create_local_body(self.district1)
        self.local_body2 = self.create_local_body(self.district2)

        self.facility1 = self.create_facility(
            district=self.district1, user=self.admin1, local_body=self.local_body1
        )
        self.facility2 = self.create_facility(
            district=self.district2, user=self.admin2, local_body=self.local_body2
        )

        self.staff1 = self.create_user(
            "staff1234", self.district1, home_facility=self.facility1
        )
        self.staff2 = self.create_user(
            "staff1235", self.district2, home_facility=self.facility2
        )

    def test_unlink_home_facility_admin_same_district(self):
        self.client.force_login(self.admin1)

        username = self.staff1.username
        response = self.client.delete(
            "/api/v1/users/" + username + "/clear_home_facility/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unlink_home_facility_admin_different_district(self):
        self.client.force_login(self.admin1)

        username = self.staff2.username
        response = self.client.delete(
            "/api/v1/users/" + username + "/clear_home_facility/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "User not found")

    def test_unlink_faciltity_admin_same_district(self):
        self.client.force_login(self.admin1)

        username = self.staff1.username

        # clear from home facility to linked facility
        response = self.client.delete(
            "/api/v1/users/" + username + "/clear_home_facility/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(
            "/api/v1/users/" + username + "/delete_facility/",
            {"facility": self.facility1.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unlink_faciltity_admin_different_district(self):
        self.client.force_login(self.admin1)

        username = self.staff2.username
        response = self.client.delete(
            "/api/v1/users/" + username + "/delete_facility/",
            {"facility": self.facility2.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "User not found")

    def test_unlink_home_facility_by_nurse(self):
        self.client.force_login(self.staff1)
        response = self.client.delete(
            f"/api/v1/users/{self.staff1.username}/clear_home_facility/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
