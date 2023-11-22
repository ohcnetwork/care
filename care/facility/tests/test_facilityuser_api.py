from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class FacilityUserTest(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

        cls.facility1 = cls.create_facility(
            cls.super_user, cls.district, cls.local_body
        )
        cls.facility2 = cls.create_facility(
            cls.super_user, cls.district, cls.local_body
        )

    def setUp(self) -> None:
        self.client.force_authenticate(self.super_user)

    def test_get_queryset_with_prefetching(self):
        response = self.client.get(
            f"/api/v1/facility/{self.facility.external_id}/get_users/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNumQueries(2)

    def test_link_new_facility(self):
        response = self.client.get("/api/v1/facility/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_link_existing_facility(self):
        response = self.client.get(
            f"/api/v1/facility/?exclude_user={self.user.username}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
