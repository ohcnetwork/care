import datetime

from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import PatientRegistration
from care.facility.models.patient_consultation import PatientConsultation
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
        cls.asset_location = cls.create_asset_location(cls.facility)
        cls.bed = cls.create_bed(facility=cls.facility, location=cls.asset_location)
        cls.admission_consultation_no_bed = cls.create_consultation(
            facility=cls.facility,
            patient=cls.patient,
            suggestion=PatientConsultation.SUGGESTION_CHOICES[1][0],  # ADMISSION
        )
        cls.domiciliary_consultation_no_bed = cls.create_consultation(
            facility=cls.facility,
            patient=cls.patient,
            suggestion=PatientConsultation.SUGGESTION_CHOICES[4][0],  # DOMICILIARY CARE
        )
        cls.consultation_with_bed = cls.create_consultation(
            facility=cls.facility, patient=cls.patient
        )
        cls.consultation_bed = cls.create_consultation_bed(
            cls.consultation_with_bed, cls.bed
        )
        cls.consultation_with_bed.current_bed = cls.consultation_bed
        cls.consultation_with_bed.save()

        cls.log_update = {
            "clone_last": False,
            "rounds_type": "NORMAL",
            "patient_category": "Comfort",
            "action": "DISCHARGE_RECOMMENDED",
            "taken_at": datetime.datetime.now().isoformat(),
        }

    def get_url(self, external_consultation_id=None):
        return f"/api/v1/consultation/{external_consultation_id}/daily_rounds/analyse/"

    def test_external_consultation_does_not_exists_returns_404(self):
        sample_uuid = "e4a3d84a-d678-4992-9287-114f029046d8"
        response = self.client.get(self.get_url(sample_uuid))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_action_in_log_update(
        self,
    ):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation_with_bed.external_id}/daily_rounds/",
            data=self.log_update,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient_category"], "Comfort Care")
        self.assertEqual(response.data["rounds_type"], "NORMAL")
        patient = PatientRegistration.objects.get(
            id=self.consultation_with_bed.patient_id
        )
        self.assertEqual(
            patient.action, PatientRegistration.ActionEnum.DISCHARGE_RECOMMENDED.value
        )

    def test_log_update_without_bed_for_admission(
        self,
    ):
        response = self.client.post(
            f"/api/v1/consultation/{self.admission_consultation_no_bed.external_id}/daily_rounds/",
            data=self.log_update,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["bed"],
            "Patient does not have a bed assigned. Please assign a bed first",
        )

    def test_log_update_without_bed_for_domiciliary(
        self,
    ):
        response = self.client.post(
            f"/api/v1/consultation/{self.domiciliary_consultation_no_bed.external_id}/daily_rounds/",
            data=self.log_update,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
