from rest_framework import status

from care.facility.models import MedibaseMedicine
from care.utils.tests.test_base import TestBase


class PrescriptionsApiTestCase(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self.medicine = MedibaseMedicine.objects.first()

        self.normal_prescription_data = {
            "medicine": self.medicine.external_id,
            "prescription_type": "REGULAR",
            "dosage": "1 mg",
            "frequency": "OD",
            "is_prn": False,
        }

    def test_create_normal_prescription(self):
        consultation = self.create_consultation()
        response = self.client.post(
            f"/api/v1/consultation/{consultation.external_id}/prescriptions/",
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
        consultation = self.create_consultation()
        res = self.client.post(
            f"/api/v1/consultation/{consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        discontinue_prescription_id = res.data["id"]

        res = self.client.post(
            f"/api/v1/consultation/{consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.post(
            f"/api/v1/consultation/{consultation.external_id}/prescriptions/{discontinue_prescription_id}/discontinue/",
            {
                "discontinued_reason": "Test Reason",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.post(
            f"/api/v1/consultation/{consultation.external_id}/prescriptions/",
            self.normal_prescription_data,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
