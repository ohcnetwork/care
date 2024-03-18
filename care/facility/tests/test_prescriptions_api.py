from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import MedibaseMedicine
from care.utils.tests.test_utils import TestUtils


class PrescriptionsApiTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(cls.district, cls.facility)

    def setUp(self) -> None:
        super().setUp()
        self.consultation = self.create_consultation(self.patient, self.facility)
        self.medicine = MedibaseMedicine.objects.first()

        self.normal_prescription_data = {
            "medicine": self.medicine.external_id,
            "prescription_type": "REGULAR",
            "base_dosage": "1 mg",
            "frequency": "OD",
            "dosage_type": "REGULAR",
        }

    def test_create_normal_prescription(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
