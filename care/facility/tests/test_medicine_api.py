from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import MedibaseMedicine, Prescription, PrescriptionDosageType
from care.utils.tests.test_utils import TestUtils


class MedicinePrescriptionApiTestCase(TestUtils, APITestCase):
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
        cls.consultation = cls.create_consultation(cls.patient, cls.facility)
        meds = MedibaseMedicine.objects.all().values_list("external_id", flat=True)[:2]
        cls.medicine1 = str(meds[0])

    def setUp(self) -> None:
        super().setUp()

    def prescription_data(self, **kwargs):
        data = {
            "medicine": self.medicine1,
            "prescription_type": "REGULAR",
            "base_dosage": "1 mg",
            "frequency": "OD",
            "dosage_type": kwargs.get(
                "dosage_type", PrescriptionDosageType.REGULAR.value
            ),
        }
        return {**data, **kwargs}

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

    def test_create_titrated_prescription(self):
        titrated_prescription_data = self.prescription_data(
            dosage_type=PrescriptionDosageType.TITRATED.value,
            target_dosage="2 mg",
            instruction_on_titration="Test Instruction",
        )
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            titrated_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        titrated_prescription_data = self.prescription_data(
            dosage_type=PrescriptionDosageType.TITRATED.value,
        )
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            titrated_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_prn_prescription(self):
        prn_prescription_data = self.prescription_data(
            dosage_type=PrescriptionDosageType.PRN.value,
            indicator="Test Indicator",
        )
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            prn_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        prn_prescription_data = self.prescription_data(
            dosage_type=PrescriptionDosageType.PRN.value,
        )
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/prescriptions/",
            prn_prescription_data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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
            "base_dosage": "1 mg",
            "frequency": "OD",
            "dosage_type": kwargs.get(
                "dosage_type", PrescriptionDosageType.REGULAR.value
            ),
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

    def test_administer_titrated_dosage(self):
        prescription = self.create_prescription(
            dosage_type=PrescriptionDosageType.TITRATED.value, target_dosage="10 mg"
        )
        res = self.client.post(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescriptions/{prescription.external_id}/administer/",
            {"notes": "Test Notes"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.post(
            f"/api/v1/consultation/{prescription.consultation.external_id}/prescriptions/{prescription.external_id}/administer/",
            {"notes": "Test Notes", "dosage": "1 mg"},
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
