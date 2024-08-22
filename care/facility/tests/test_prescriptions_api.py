from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import MedibaseMedicine, Prescription
from care.utils.tests.test_utils import TestUtils


class PrescriptionsApiTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("nurse1", cls.district, home_facility=cls.facility)
        cls.remote_facility = cls.create_facility(
            cls.super_user, cls.district, cls.local_body
        )
        cls.remote_user = cls.create_user(
            "remote-nurse", cls.district, home_facility=cls.remote_facility
        )
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.consultation = cls.create_consultation(cls.patient, cls.facility)
        cls.discharged_patient = cls.create_patient(cls.district, cls.facility)
        cls.discharged_consultation = cls.create_consultation(
            cls.patient, cls.facility, discharge_date="2002-04-01T16:30:00Z"
        )

    def setUp(self) -> None:
        super().setUp()
        self.medicine, self.medicine_2 = MedibaseMedicine.objects.all()[:2]
        self.normal_prescription_data = {
            "medicine": self.medicine.external_id,
            "prescription_type": "REGULAR",
            "base_dosage": "1 mg",
            "frequency": "OD",
            "dosage_type": "REGULAR",
        }
        self.normal_prescription_data_2 = {
            "medicine": self.medicine_2.external_id,
            "prescription_type": "REGULAR",
            "base_dosage": "1 mg",
            "frequency": "OD",
            "dosage_type": "REGULAR",
        }
        self.discharged_consultation_prescription = Prescription.objects.create(
            consultation=self.discharged_consultation,
            medicine=self.medicine,
        )

    def prescription_data(self, **kwargs):
        data = self.normal_prescription_data
        data.update(**kwargs)
        return data

    def test_create_normal_prescription(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_prescription_non_home_facility(self):
        self.client.force_authenticate(self.remote_user)
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_prescription_on_discharged_consultation(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.discharged_consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discontinue_prescription_on_discharged_consultation(self):
        res = self.client.post(
            f"/api/v1/consultation/{self.discharged_consultation.external_id}/prescriptions/{self.discharged_consultation_prescription.external_id}/discontinue/",
            {
                "discontinued_reason": "Test Reason",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_dosage(self):
        data = self.prescription_data(base_dosage="abc")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.json()["base_dosage"][0],
            "Invalid Input, must be in the format: <amount> <unit>",
        )

    def test_dosage_out_of_range(self):
        data = self.prescription_data(base_dosage="10000 mg")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.json()["base_dosage"][0],
            "Input amount must be between 0.0001 and 5000",
        )

        data = self.prescription_data(base_dosage="-1 mg")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.json()["base_dosage"][0],
            "Input amount must be between 0.0001 and 5000",
        )

    def test_dosage_precision(self):
        data = self.prescription_data(base_dosage="0.300003 mg")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.json()["base_dosage"][0],
            "Input amount must have at most 4 decimal places",
        )

    def test_dosage_unit_invalid(self):
        data = self.prescription_data(base_dosage="1 abc")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(res.json()["base_dosage"][0].startswith("Unit must be one of"))

    def test_dosage_leading_zero(self):
        data = self.prescription_data(base_dosage="01 mg")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.json()["base_dosage"][0],
            "Input amount must be a valid number without leading or trailing zeroes",
        )

    def test_dosage_trailing_zero(self):
        data = self.prescription_data(base_dosage="1.0 mg")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.json()["base_dosage"][0],
            "Input amount must be a valid number without leading or trailing zeroes",
        )

    def test_dosage_validator_clean(self):
        data = self.prescription_data(base_dosage=" 1 mg ")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_valid_dosage(self):
        data = self.prescription_data(base_dosage="1 mg")
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            data,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_prescribe_duplicate_active_medicine_and_discontinue(self):
        """
        1. Creates a prescription with Medicine A
        2. Attempts to create another prescription with Medicine A (expecting failure)
        3. Discontinues the first prescription
        4. Re-attempts to create another prescription with Medicine A (expecting success)
        """
        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        discontinue_prescription_id = res.data["id"]

        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/{discontinue_prescription_id}/discontinue/",
            {
                "discontinued_reason": "Test Reason",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_titrated_prescription(self):
        titrated_prescription_data = {
            **self.normal_prescription_data,
            "dosage_type": "TITRATED",
            "target_dosage": "2 mg",
        }
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            titrated_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        titrated_prescription_data = {
            **self.normal_prescription_data,
            "dosage_type": "TITRATED",
        }
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            titrated_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_prn_prescription(self):
        prn_prescription_data = {
            **self.normal_prescription_data,
            "dosage_type": "PRN",
            "indicator": "Test Indicator",
        }
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            prn_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        prn_prescription_data = {
            **self.normal_prescription_data,
            "dosage_type": "PRN",
        }
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            prn_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medicine_filter_for_prescription(self):
        # post 2 prescriptions with different medicines
        self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data_2,
        )

        # get all prescriptions without medicine filter
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
        )
        self.assertEqual(response.data["count"], 2)

        # get all prescriptions with medicine filter
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/?medicine={self.medicine.external_id}",
        )

        for prescription in response.data["results"]:
            self.assertEqual(
                prescription["medicine_object"]["name"], self.medicine.name
            )
