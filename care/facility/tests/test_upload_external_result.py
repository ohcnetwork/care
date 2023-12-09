from rest_framework import status
from rest_framework.test import APITestCase

from care.utils.tests.test_utils import TestUtils


class PatientExternalTestViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.ward = cls.create_ward(cls.local_body)
        cls.ward1 = cls.create_ward(cls.local_body)
        cls.user = cls.create_super_user("su", cls.district)

    def test_no_data_upload(self):
        response = self.client.post(
            "/api/v1/external_result/bulk_upsert/", sample_data={}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["sample_tests"], "No Data was provided")

    def test_different_district_upload(self):
        sample_data = {
            "sample_tests": [
                {
                    "district": "Random_district",
                    "srf_id": "00/EKM/0000",
                    "name": "Test Upload0",
                    "age": 24,
                    "age_in": "years",
                    "gender": "m",
                    "mobile_number": 8888888888,
                    "address": "Upload test address",
                    "ward": 7,
                    "local_body": "Poothrikka",
                    "local_body_type": "grama panchayath",
                    "source": "Secondary contact aparna",
                    "sample_collection_date": "2020-10-14",
                    "result_date": "2020-10-14",
                    "test_type": "Antigen",
                    "lab_name": "Karothukuzhi Laboratory",
                    "sample_type": "Ag-SD_Biosensor_Standard_Q_COVID-19_Ag_detection_kit",
                    "patient_status": "Asymptomatic",
                    "is_repeat": "NO",
                    "patient_category": "Cat 17: All individuals who wish to get themselves tested",
                    "result": "Negative",
                }
            ]
        }

        response = self.client.post(
            "/api/v1/external_result/bulk_upsert/", sample_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["Error"], "User must belong to same district")

    def test_same_district_upload(self):
        sample_data = {
            "sample_tests": [
                {
                    "district": str(self.district),
                    "srf_id": "00/EKM/0000",
                    "name": "Test Upload0",
                    "age": 24,
                    "age_in": "years",
                    "gender": "m",
                    "mobile_number": 8888888888,
                    "address": "Upload test address",
                    "ward": self.ward.id,
                    "local_body": str(self.local_body.name),
                    "local_body_type": "municipality",
                    "source": "Secondary contact aparna",
                    "sample_collection_date": "2020-10-14",
                    "result_date": "2020-10-14",
                    "test_type": "Antigen",
                    "lab_name": "Karothukuzhi Laboratory",
                    "sample_type": "Ag-SD_Biosensor_Standard_Q_COVID-19_Ag_detection_kit",
                    "patient_status": "Asymptomatic",
                    "is_repeat": "NO",
                    "patient_category": "Cat 17: All individuals who wish to get themselves tested",
                    "result": "Negative",
                }
            ]
        }

        response = self.client.post(
            "/api/v1/external_result/bulk_upsert/", sample_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
