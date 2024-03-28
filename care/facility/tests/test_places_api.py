from rest_framework import status
from rest_framework.test import APITestCase

from care.users.models import Ward
from care.utils.tests.test_utils import TestUtils


class DistrictViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

    def test_list_district(self):
        response = self.client.get("/api/v1/district/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_district(self):
        response = self.client.get(
            f"/api/v1/district/{self.district.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_district_all_local_body(self):
        response = self.client.get(
            f"/api/v1/district/{self.district.id}/get_all_local_body/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_district_local_body(self):
        response = self.client.get(
            f"/api/v1/district/{self.district.id}/local_bodies/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LocalBodyViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

    def test_list_local_body(self):
        response = self.client.get("/api/v1/local_body/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_local_body(self):
        response = self.client.get(
            f"/api/v1/local_body/{self.local_body.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StateViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)

    def test_list_state(self):
        response = self.client.get("/api/v1/state/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_state(self):
        response = self.client.get(
            f"/api/v1/state/{self.state.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_state_districts(self):
        response = self.client.get(
            f"/api/v1/state/{self.state.id}/districts/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class WardViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff", cls.district, home_facility=cls.facility)
        cls.ward = cls.create_ward(cls.local_body)

    def test_list_ward(self):
        response = self.client.get("/api/v1/ward/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_ward(self):
        response = self.client.get(
            f"/api/v1/ward/{self.ward.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
