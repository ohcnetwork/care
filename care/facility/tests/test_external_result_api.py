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
        cls.external_result = cls.create_patient_external_test(
            cls.district, cls.local_body, cls.ward, name="TEST_1"
        )

    def test_list_external_result(self):
        state2 = self.create_state()
        district2 = self.create_district(state2)
        local_body2 = self.create_local_body(district2)
        ward2 = self.create_ward(local_body2)

        self.create_patient_external_test(
            district2, local_body2, ward2, name="TEST_2", mobile_number="9999988888"
        )
        self.create_patient_external_test(
            self.district, self.local_body, self.ward, srf_id="ID001"
        )

        response = self.client.get("/api/v1/external_result/")
        patient_external_test = PatientExternalTest.objects.all()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], len(patient_external_test))

        response = self.client.get("/api/v1/external_result/?name=TEST_2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "TEST_2")

        response = self.client.get("/api/v1/external_result/?srf_id=ID001")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["srf_id"], "ID001")

        response = self.client.get(f"/api/v1/external_result/?ward__id={self.ward.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["ward_object"]["name"], self.ward.name
        )

        response = self.client.get(
            f"/api/v1/external_result/?district__id={self.district.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["district_object"]["name"], self.district.name
        )

        response = self.client.get(
            f"/api/v1/external_result/?local_body={self.local_body.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["local_body_object"]["name"],
            self.local_body.name,
        )

        response = self.client.get("/api/v1/external_result/?mobile_number=9999988888")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["mobile_number"], "9999988888")
        self.assertEqual(response.data["results"][0]["name"], "TEST_2")

    def test_retrieve_external_result(self):
        response = self.client.get(
            f"/api/v1/external_result/{self.external_result.id}/"
        )
        patient_external_test = PatientExternalTest.objects.get(
            id=self.external_result.id
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), patient_external_test.id)
        self.assertEqual(response.data.get("name"), patient_external_test.name)

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
        state2 = self.create_state()
        district2 = self.create_district(state2)
        external_test_data = self.get_patient_external_test_data(
            str(district2), str(self.local_body.name), self.ward.number
        ).copy()
        sample_data = {"sample_tests": [external_test_data]}
        response = self.client.post(
            "/api/v1/external_result/bulk_upsert/", sample_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["Error"], "User must belong to same district")

    def test_same_district_upload(self):
        external_test_data = self.get_patient_external_test_data(
            str(self.district), str(self.local_body.name), self.ward.number
        ).copy()
        external_test_data.update({"local_body_type": "municipality"})
        sample_data = {"sample_tests": [external_test_data]}
        response = self.client.post(
            "/api/v1/external_result/bulk_upsert/", sample_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
