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
