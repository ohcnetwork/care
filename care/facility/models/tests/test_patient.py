from datetime import timedelta

from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import DiseaseStatusEnum
from care.utils.tests.test_utils import TestUtils


class PatientRegistrationTest(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(cls.district, cls.facility)

    def test_disease_state_recovery_is_aliased_to_recovered(self):
        patient = self.patient

        patient.disease_status = DiseaseStatusEnum.RECOVERY.value
        patient.save(update_fields=["disease_status"])
        patient.refresh_from_db()

        self.assertEqual(patient.disease_status, DiseaseStatusEnum.RECOVERED.value)

    def test_date_of_birth_validation(self):
        dist_admin = self.create_user("dist_admin", self.district, user_type=30)
        sample_data = {
            "facility": self.facility.external_id,
            "blood_group": "AB+",
            "gender": 1,
            "date_of_birth": now().date() + timedelta(days=365),
            "year_of_birth": None,
            "disease_status": "NEGATIVE",
            "emergency_phone_number": "+919000000666",
            "is_vaccinated": "false",
            "number_of_doses": 0,
            "phone_number": "+919000044343",
        }
        self.client.force_authenticate(user=dist_admin)
        response = self.client.post("/api/v1/patient/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_of_birth", response.data)

    def test_year_of_birth_validation(self):
        dist_admin = self.create_user("dist_admin", self.district, user_type=30)
        sample_data = {
            "facility": self.facility.external_id,
            "blood_group": "AB+",
            "gender": 1,
            "date_of_birth": None,
            "year_of_birth": now().year + 1,
            "disease_status": "NEGATIVE",
            "emergency_phone_number": "+919000000666",
            "is_vaccinated": "false",
            "number_of_doses": 0,
            "phone_number": "+919000044343",
        }
        self.client.force_authenticate(user=dist_admin)
        response = self.client.post("/api/v1/patient/", sample_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("year_of_birth", response.data)
