import datetime

from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import PatientRegistration
from care.utils.tests.test_utils import TestUtils


class TestDailyRoundApi(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(district=cls.district, facility=cls.facility)
        cls.consultation = cls.create_consultation(
            facility=cls.facility, patient=cls.patient
        )

    def get_url(self, external_consultation_id=None):
        return f"/api/v1/consultation/{external_consultation_id}/daily_rounds/analyse/"

    def test_external_consultation_does_not_exists_returns_404(self):
        sample_uuid = "e4a3d84a-d678-4992-9287-114f029046d8"
        response = self.client.get(self.get_url(sample_uuid))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_action_in_log_update(
        self,
    ):
        log_update = {
            "clone_last": False,
            "rounds_type": "NORMAL",
            "patient_category": "Comfort",
            "action": "DISCHARGE_RECOMMENDED",
            "taken_at": datetime.datetime.now().isoformat(),
        }
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/daily_rounds/",
            data=log_update,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient_category"], "Comfort Care")
        self.assertEqual(response.data["rounds_type"], "NORMAL")
        patient = PatientRegistration.objects.get(id=self.consultation.patient_id)
        self.assertEqual(
            patient.action, PatientRegistration.ActionEnum.DISCHARGE_RECOMMENDED.value
        )
