from rest_framework import status
from rest_framework.test import APITestCase

from care.users.models import District, LocalBody, State, Ward
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
        cls.ward = cls.create_ward(cls.local_body)

    def test_list_district(self):
        state2 = self.create_state(name="TEST_STATE_2")
        self.create_district(state2, name="TEST_DISTRICT_2")

        response = self.client.get("/api/v1/district/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/api/v1/district/?district_name=TEST_DISTRICT_2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "TEST_DISTRICT_2")

        response = self.client.get(f"/api/v1/district/?state={state2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "TEST_DISTRICT_2")

        response = self.client.get(f"/api/v1/district/?state_name={self.state.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.district.name)

    def test_retrieve_district(self):
        response = self.client.get(f"/api/v1/district/{self.district.id}/")
        district_obj = District.objects.get(pk=self.district.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), district_obj.id)
        self.assertEqual(response.data.get("name"), district_obj.name)

    def test_list_district_all_local_body(self):
        response = self.client.get(
            f"/api/v1/district/{self.district.id}/get_all_local_body/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], self.local_body.name)
        self.assertEqual(response.data[0]["wards"][0]["name"], self.ward.name)

    def test_list_district_local_body(self):
        response = self.client.get(
            f"/api/v1/district/{self.district.id}/local_bodies/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], self.local_body.name)


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
        state2 = self.create_state(name="TEST_STATE_2")
        district2 = self.create_district(state2)
        self.create_local_body(district2, name="LOCAL_BODY_2")

        response = self.client.get("/api/v1/local_body/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            f"/api/v1/local_body/?local_body_name={self.local_body.name}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.local_body.name)

        response = self.client.get(f"/api/v1/local_body/?state={state2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "LOCAL_BODY_2")

        response = self.client.get(f"/api/v1/local_body/?state_name={self.state.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.local_body.name)

        response = self.client.get(f"/api/v1/local_body/?district={self.district.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.local_body.name)

        response = self.client.get(f"/api/v1/local_body/?district2={district2.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "LOCAL_BODY_2")

    def test_retrieve_local_body(self):
        response = self.client.get(f"/api/v1/local_body/{self.local_body.id}/")
        local_body_obj = LocalBody.objects.get(pk=self.local_body.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), local_body_obj.id)
        self.assertEqual(response.data.get("name"), local_body_obj.name)


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
        self.assertEqual(response.data["count"], len(State.objects.all()))

    def test_retrieve_state(self):
        response = self.client.get(f"/api/v1/state/{self.state.id}/")
        state_obj = State.objects.get(pk=self.state.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), state_obj.id)
        self.assertEqual(response.data.get("name"), state_obj.name)

    def test_list_state_districts(self):
        response = self.client.get(f"/api/v1/state/{self.state.id}/districts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], self.district.name)


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
        state2 = self.create_state(name="TEST_STATE_2")
        district2 = self.create_district(state2)
        local_body2 = self.create_local_body(district2)
        self.create_ward(local_body2, name="WARD2")

        # Endpoints to filter with state id and state name are throwing error

        response = self.client.get("/api/v1/ward/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/api/v1/ward/?ward_name=WARD2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "WARD2")

        response = self.client.get(f"/api/v1/ward/?district={district2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "WARD2")

        response = self.client.get(f"/api/v1/ward/?district_name={self.district.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.ward.name)

        response = self.client.get(f"/api/v1/ward/?local_body={self.local_body.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.ward.name)
        self.assertEqual(response.data["results"][0]["local_body"], self.local_body.id)

        response = self.client.get(f"/api/v1/ward/?local_body_name={local_body2.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "WARD2")

        response = self.client.get(f"/api/v1/ward/?state_name={state2.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "WARD2")

        response = self.client.get(f"/api/v1/ward/?state={self.state.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], self.ward.name)

    def test_retrieve_ward(self):
        response = self.client.get(f"/api/v1/ward/{self.ward.id}/")
        ward_obj = Ward.objects.get(pk=self.ward.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), ward_obj.id)
        self.assertEqual(response.data.get("name"), ward_obj.name)
