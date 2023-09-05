import collections.abc
from enum import Enum

from django.conf import settings
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.api.viewsets.facility import AllFacilityViewSet, FacilityViewSet
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedLocalBodyObject(Enum):
    ID = "id"
    NAME = "name"
    BODY_TYPE = "body_type"
    LOCALBODY_CODE = "localbody_code"
    DISTRICT = "district"


class ExpectedFacilityListKeys(Enum):
    ID = "id"
    NAME = "name"
    MODIFIED_DATE = "modified_date"
    CREATED_DATE = "created_date"
    KASP_EMPANELLED = "kasp_empanelled"
    FACILITY_TYPE = "facility_type"
    FEATURES = "features"
    LOCAL_BODY_OBJECT = "local_body_object"
    PHONE_NUMBER = "phone_number"
    READ_COVER_IMAGE_URL = "read_cover_image_url"
    PATIENT_COUNT = "patient_count"
    BED_COUNT = "bed_count"


class ExpectedWardKeys(Enum):
    ID = "id"
    NAME = "name"
    NUMBER = "number"
    LOCAL_BODY = "local_body"


class ExpectedDistrictKeys(Enum):
    ID = "id"
    NAME = "name"
    STATE = "state"


class ExpectedStateKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedFacilityRetrieveKeys(Enum):
    ID = "id"
    NAME = "name"
    WARD = "ward"
    LOCAL_BODY = "local_body"
    DISTRICT = "district"
    STATE = "state"
    FACILITY_TYPE = "facility_type"
    ADDRESS = "address"
    LONGITUDE = "longitude"
    LATITUDE = "latitude"
    FEATURES = "features"
    PINCODE = "pincode"
    OXYGEN_CAPACITY = "oxygen_capacity"
    PHONE_NUMBER = "phone_number"
    WARD_OBJECT = "ward_object"
    LOCAL_BODY_OBJECT = "local_body_object"
    DISTRICT_OBJECT = "district_object"
    STATE_OBJECT = "state_object"
    MODIFIED_DATE = "modified_date"
    CREATED_DATE = "created_date"
    KASP_EMPANELLED = "kasp_empanelled"
    MIDDLEWARE_ADDRESS = "middleware_address"
    EXPECTED_OXYGEN_REQUIREMENT = "expected_oxygen_requirement"
    TYPE_B_CYLINDERS = "type_b_cylinders"
    TYPE_C_CYLINDERS = "type_c_cylinders"
    TYPE_D_CYLINDERS = "type_d_cylinders"
    EXPECTED_TYPE_B_CYLINDERS = "expected_type_b_cylinders"
    EXPECTED_TYPE_C_CYLINDERS = "expected_type_c_cylinders"
    EXPECTED_TYPE_D_CYLINDERS = "expected_type_d_cylinders"
    READ_COVER_IMAGE_URL = "read_cover_image_url"
    PATIENT_COUNT = "patient_count"
    BED_COUNT = "bed_count"


class FacilityTests(TestClassMixin, TestBase, APITestCase):
    FACILITY_CAPACITY_CSV_KEY = "capacity"
    FACILITY_DOCTORS_CSV_KEY = "doctors"
    FACILITY_TRIAGE_CSV_KEY = "triage"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

    def setUp(self):
        # Refresh token to header
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_facilities(self):
        response = self.client.get("/api/v1/facility/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedFacilityListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

        local_body_object_keys = [key.value for key in ExpectedLocalBodyObject]

        # if data["local_body_object"] is not None:
        self.assertCountEqual(data["local_body_object"].keys(), local_body_object_keys)

        # Ensure the data is coming in correctly
        data = response.json()["results"][0]
        self.assertIsInstance(data["id"], str)
        self.assertIsInstance(data["name"], str)
        self.assertIsInstance(data["modified_date"], str)
        self.assertIsInstance(data["created_date"], str)
        self.assertIsInstance(data["kasp_empanelled"], bool)
        self.assertIsInstance(data["facility_type"], str)
        self.assertIsInstance(data["features"], list)
        self.assertIsInstance(data["local_body_object"]["id"], int)
        self.assertIsInstance(data["local_body_object"]["name"], str)
        self.assertIsInstance(data["local_body_object"]["body_type"], int)
        self.assertIsInstance(data["local_body_object"]["localbody_code"], str)
        self.assertIsInstance(data["local_body_object"]["district"], int)
        self.assertIsInstance(data["phone_number"], str)
        self.assertIsNone(data["read_cover_image_url"])
        self.assertIsInstance(data["patient_count"], int)
        self.assertIsInstance(data["bed_count"], int)

        # Test without CSV request parameter
        response = self.client.get("/api/v1/facility/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Test with CSV request parameter and FACILITY_CAPACITY_CSV_KEY
        response = self.client.get(
            "/api/v1/facility/",
            {
                settings.CSV_REQUEST_PARAMETER: "true",
                self.FACILITY_CAPACITY_CSV_KEY: "true",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.streaming_content, collections.abc.Iterable)

        # Test with CSV request parameter and FACILITY_DOCTORS_CSV_KEY
        response = self.client.get(
            "/api/v1/facility/",
            {
                settings.CSV_REQUEST_PARAMETER: "true",
                self.FACILITY_DOCTORS_CSV_KEY: "true",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.streaming_content, collections.abc.Iterable)

        # Test with CSV request parameter and FACILITY_TRIAGE_CSV_KEY
        response = self.client.get(
            "/api/v1/facility/",
            {
                settings.CSV_REQUEST_PARAMETER: "true",
                self.FACILITY_TRIAGE_CSV_KEY: "true",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.streaming_content, collections.abc.Iterable)

        response = self.client.get(
            "/api/v1/facility/", {settings.CSV_REQUEST_PARAMETER: "true"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.streaming_content, collections.abc.Iterable)

    def test_retrieve_facility(self):
        response = self.client.get(f"/api/v1/facility/{self.facility.external_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), dict)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedFacilityRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        ward_object_keys = [key.value for key in ExpectedWardKeys]
        self.assertCountEqual(data["ward_object"].keys(), ward_object_keys)

        local_body_object_keys = [key.value for key in ExpectedLocalBodyObject]
        self.assertCountEqual(data["local_body_object"].keys(), local_body_object_keys)

        district_object_keys = [key.value for key in ExpectedDistrictKeys]
        self.assertCountEqual(data["district_object"].keys(), district_object_keys)

        state_object_keys = [key.value for key in ExpectedStateKeys]
        self.assertCountEqual(data["state_object"].keys(), state_object_keys)

        # Ensure the data is coming in correctly
        data = response.json()
        self.assertIsInstance(data["id"], str)
        self.assertIsInstance(data["name"], str)
        self.assertIsInstance(data["ward"], int)
        self.assertIsInstance(data["local_body"], int)
        self.assertIsInstance(data["district"], int)
        self.assertIsInstance(data["state"], int)
        self.assertIsInstance(data["facility_type"], str)
        self.assertIsInstance(data["address"], str)
        self.assertIsNone(data["longitude"])
        self.assertIsNone(data["latitude"])
        self.assertIsInstance(data["features"], list)
        self.assertIsInstance(data["pincode"], int)
        self.assertIsInstance(data["oxygen_capacity"], int)
        self.assertIsInstance(data["phone_number"], str)

    def test_all_listing(self):
        response = self.new_request(
            ("/api/v1/getallfacilitiess/",), {"get": "list"}, AllFacilityViewSet
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_listing(self):
        response = self.new_request(
            ("/api/v1/facility/",), {"get": "list"}, FacilityViewSet, self.user
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        user = self.user
        sample_data = {
            "name": "Hospital X",
            "ward": user.ward.pk,
            "local_body": user.local_body.pk,
            "district": user.district.pk,
            "state": user.state.pk,
            "facility_type": "Educational Inst",
            "address": "Nearby",
            "pincode": 390024,
            "features": [],
        }
        response = self.new_request(
            ("/api/v1/facility/", sample_data, "json"),
            {"post": "create"},
            FacilityViewSet,
            user,
        )
        fac_id = response.data["id"]
        self.assertIs(response.status_code, status.HTTP_201_CREATED)

        retrieve_response = self.new_request(
            (f"/api/v1/facility/{fac_id}",),
            {"get": "retrieve"},
            FacilityViewSet,
            user,
            {"external_id": fac_id},
        )

        self.assertIs(retrieve_response.status_code, status.HTTP_200_OK)

    def test_no_auth(self):
        response = self.new_request(
            ("/api/v1/facility/",),
            {"get": "list"},
            FacilityViewSet,
        )
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

        sample_data = {}
        create_response = self.new_request(
            ("/api/v1/facility/", sample_data, "json"),
            {"post": "create"},
            FacilityViewSet,
        )
        self.assertIs(create_response.status_code, status.HTTP_403_FORBIDDEN)

    # TODO: Fix the destroy method of facility
    # def test_destroy(self):
    #     superuser = self.create_user(district=self.district, username ="test1", facility=self.facility)
    #     superuser.is_superuser = True
    #     superuser.save()
    #     superuser.refresh_from_db()
    #     client = APIClient()
    #     client.credentials(
    #         HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(superuser).access_token}"
    #     )
    #     facility = self.facility
    #     url = f"/api/v1/facility/{facility.external_id}/"
    #     response = self.client.delete(url)
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    #     districtlabadmin = self.create_user(facility=self.facility, type = User.TYPE_VALUE_MAP["DistrictLabAdmin"])
    #     client = APIClient()
    #     client.credentials(
    #         HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(districtlabadmin).access_token}"
    #     )
    #     response = client.delete(url)
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    #     staff = self.create_user(facility=self.facility, type = User.TYPE_VALUE_MAP["Staff"])
    #     client = APIClient()
    #     client.credentials(
    #         HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(staff).access_token}"
    #     )
    #     response = self.client.delete(url)
    #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    #     PatientRegistration.objects.create(facility=self.facility, is_active=True)
    #     url = f"/api/v1/facility/{facility.external_id}/"
    #     response = self.client.delete(url)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
