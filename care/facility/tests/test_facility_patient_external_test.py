from enum import Enum

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.utils.tests.test_utils import TestUtils


class ExpectedPatientExternalTestListKeys(Enum):
    id = "id"
    name = "name"
    age = "age"
    age_in = "age_in"
    test_type = "test_type"
    result = "result"
    patient_created = "patient_created"
    result_date = "result_date"


class ExpectedPatientExternalTestRetrieveKeys(Enum):
    id = "id"
    ward_object = "ward_object"
    local_body_object = "local_body_object"
    district_object = "district_object"
    sample_collection_date = "sample_collection_date"
    result_date = "result_date"
    external_id = "external_id"
    created_date = "created_date"
    modified_date = "modified_date"
    deleted = "deleted"
    srf_id = "srf_id"
    name = "name"
    age = "age"
    age_in = "age_in"
    gender = "gender"
    address = "address"
    mobile_number = "mobile_number"
    is_repeat = "is_repeat"
    patient_status = "patient_status"
    source = "source"
    patient_category = "patient_category"
    lab_name = "lab_name"
    test_type = "test_type"
    sample_type = "sample_type"
    result = "result"
    patient_created = "patient_created"
    ward = "ward"
    local_body = "local_body"
    district = "district"


class WardKeys(Enum):
    ID = "id"
    NAME = "name"
    NUMBER = "number"
    LOCAL_BODY = "local_body"


class LocalBodyKeys(Enum):
    ID = "id"
    NAME = "name"
    BODY_TYPE = "body_type"
    LOCALBODY_CODE = "localbody_code"
    DISTRICT = "district"


class DistrictKeys(Enum):
    ID = "id"
    NAME = "name"
    STATE = "state"


class PatientExternalTestViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.super_user = cls.create_super_user(username="su2", district=cls.district)
        cls.local_body = cls.create_local_body(cls.district)
        cls.ward = cls.create_ward(cls.local_body)
        cls.patient_external = cls.create_patient_external_test(
            district=cls.district, local_body=cls.local_body, ward=cls.ward
        )

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.super_user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_patient_external_test(self):
        response = self.client.get("/api/v1/external_result/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedPatientExternalTestListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

    def test_retrieve_patient_external_test(self):
        response = self.client.get(
            f"/api/v1/external_result/{self.patient_external.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_keys = [key.value for key in ExpectedPatientExternalTestRetrieveKeys]

        data = response.json()

        self.assertCountEqual(data.keys(), expected_keys)

        self.assertCountEqual(
            data["ward_object"].keys(), [key.value for key in WardKeys]
        )
        self.assertCountEqual(
            data["local_body_object"].keys(), [key.value for key in LocalBodyKeys]
        )
        self.assertCountEqual(
            data["district_object"].keys(), [key.value for key in DistrictKeys]
        )
