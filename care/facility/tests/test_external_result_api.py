from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import PatientExternalTest
from care.utils.tests.test_utils import TestUtils


class PatientExternalTestViewSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.ward = cls.create_ward(cls.local_body)
        cls.user = cls.create_super_user("su", cls.district)
        cls.external_result = PatientExternalTest.objects.create(
            district=cls.district,
            srf_id="00/EKM/0000",
            name="Test Upload0",
            age=24,
            age_in="years",
            gender="m",
            mobile_number=8888888888,
            address="Upload test address",
            ward=cls.ward,
            local_body=cls.local_body,
            source="Secondary contact aparna",
            sample_collection_date="2020-10-14",
            result_date="2020-10-14",
            test_type="Antigen",
            lab_name="Karothukuzhi Laboratory",
            sample_type="Ag-SD_Biosensor_Standard_Q_COVID-19_Ag_detection_kit",
            patient_status="Asymptomatic",
            is_repeat=True,
            patient_category="Cat 17: All individuals who wish to get themselves tested",
            result="Negative",
        )

    def test_list_external_result(self):
        response = self.client.get("/api/v1/external_result/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_external_result(self):
        response = self.client.get(
            f"/api/v1/external_result/{self.external_result.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_patient_external_result(self):
        sample_data = {
            "address": "Upload test address Updated",
        }
        response = self.client.put(
            f"/api/v1/external_result/{self.external_result.id}/", sample_data
        )
        self.external_result.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.external_result.address, sample_data["address"])

    def test_update_patch_patient_external_result(self):
        sample_data = {
            "address": "Upload test address Updated patch",
        }
        response = self.client.patch(
            f"/api/v1/external_result/{self.external_result.id}/", sample_data
        )
        self.external_result.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.external_result.address, sample_data["address"])

    def test_delete_patient_external_result(self):
        response = self.client.delete(
            f"/api/v1/external_result/{self.external_result.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PatientExternalTest.objects.filter(id=self.external_result.id).exists()
        )

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
                    "ward": self.ward.number,
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
                    "ward": self.ward.number,
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
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
