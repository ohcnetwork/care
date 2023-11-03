from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class UnlinkDistrictAdmin(TestUtils, APITestCase):
    def setUp(self):
        settings.DISABLE_RATELIMIT = True
        self.state = self.create_state()

        self.district1 = self.create_district(self.state)
        self.admin1 = self.create_super_user(self.district1, username="user12345678")
        self.staff1 = self.create_user(self.district1, username="staff1234")

        self.district2 = self.create_district(self.state)
        self.admin2 = self.create_super_user(self.district2, username="user12345679")
        self.staff2 = self.create_user(self.district2, username="staff1235")

        self.facility1 = self.create_facility(district=self.district1, user=self.admin1)
        self.facility2 = self.create_facility(district=self.district2, user=self.admin2)

    def test_unlink_district_admins_same_district(self):
        self.client.force_login(self.admin1)

        # Assign a facility as home facility.
        username = self.staff1.username
        response = self.client.put(
            "/api/v1/users/" + username + "/",
            {
                "home_facility": self.facility1.external_id,
                "verified": True,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.staff1 = self.create_user(self.district2, username="staff1234")

        response = self.client.put(
            "/api/v1/users/" + username + "/",
            {"home_facility": self.facility1.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unlink_district_admins_different_district(self):
        self.client.force_login(self.admin1)

        # Assign a facility as home facility.
        username = self.staff1.username
        response = self.client.put(
            "/api/v1/users/" + username + "/",
            {
                "home_facility": self.facility1.external_id,
                "verified": True,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        anotherResponse = self.client.put(
            "/api/v1/users/" + username + "/",
            {"home_facility": self.facility2.external_id},
        )
        self.assertEqual(anotherResponse.status_code, status.HTTP_400_BAD_REQUEST)
