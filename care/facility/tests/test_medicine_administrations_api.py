from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import MedibaseMedicine, Prescription
from care.utils.tests.test_utils import TestUtils


class MedicineAdministrationsApiTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )

    def setUp(self) -> None:
        super().setUp()
        self.normal_prescription = self.create_prescription()

    def create_prescription(self, **kwargs):
        data = {
            "consultation": self.create_consultation(self.patient, self.facility),
            "medicine": MedibaseMedicine.objects.first(),
            "prescription_type": "REGULAR",
            "dosage": "1 mg",
            "frequency": "OD",
            "is_prn": False,
        }
        return Prescription.objects.create(
            **{**data, **kwargs, "prescribed_by": self.user}
        )

    def test_administer_and_archive(self):
        # test administer
        prescription = self.normal_prescription
        res = self.client.post(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescriptions/{prescription.external_id}/administer/",
            {"notes": "Test Notes"},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        administration_id = res.data["id"]

        # test archive
        archive_path = f"/api/v1/consultation/{prescription.consultation.external_id}/prescription_administration/{administration_id}/archive/"
        res = self.client.post(archive_path, {})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # test archive again
        res = self.client.post(archive_path, {})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # test list administrations
        res = self.client.get(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescription_administration/"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any([administration_id == x["id"] for x in res.data["results"]])
        )

        # test archived list administrations
        res = self.client.get(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescription_administration/?archived=true"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any([administration_id == x["id"] for x in res.data["results"]])
        )

        # test archived list administrations
        res = self.client.get(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescription_administration/?archived=false"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(
            any([administration_id == x["id"] for x in res.data["results"]])
        )

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
