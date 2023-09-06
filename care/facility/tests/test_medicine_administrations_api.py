from django.utils import timezone
from rest_framework import status

from care.facility.models import MedibaseMedicine, Prescription
from care.utils.tests.test_base import TestBase


class MedicineAdministrationsApiTestCase(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self.normal_prescription = self.create_prescription()

    def create_prescription(self, **kwargs):
        data = {
            "consultation": self.create_consultation(),
            "medicine": MedibaseMedicine.objects.first(),
            "prescription_type": "REGULAR",
            "dosage": "1 mg",
            "frequency": "OD",
            "is_prn": False,
        }
        return Prescription.objects.create(
            **{**data, **kwargs, "prescribed_by": self.user}
        )

    def test_administer(self):
        prescription = self.normal_prescription
        res = self.client.post(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescriptions/{prescription.external_id}/administer/",
            {"notes": "Test Notes"},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_administer_in_future(self):
        prescription = self.normal_prescription
        res = self.client.post(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescriptions/{prescription.external_id}/administer/",
            {"notes": "Test Notes", "administered_date": "2300-09-01T16:34"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_administer_in_past(self):
        prescription = self.normal_prescription
        res = self.client.post(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescriptions/{prescription.external_id}/administer/",
            {"notes": "Test Notes", "administered_date": "2019-09-01T16:34"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_administer_discontinued(self):
        prescription = self.create_prescription(
            discontinued=True, discontinued_date=timezone.now()
        )
        res = self.client.post(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescriptions/{prescription.external_id}/administer/",
            {"notes": "Test Notes"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
