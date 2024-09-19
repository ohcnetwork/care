import datetime
from datetime import timedelta

from django.utils import timezone
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
        cls.state_admin = cls.create_user(
            "state_admin", cls.district, home_facility=cls.facility, user_type=40
        )
        cls.district_admin = cls.create_user(
            "district_admin", cls.district, home_facility=cls.facility, user_type=30
        )
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

    def test_log_update_access_by_state_admin(self):
        self.client.force_authenticate(user=self.state_admin)
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation_with_bed.external_id}/daily_rounds/",
            data=self.log_update,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_log_update_access_by_district_admin(self):
        self.client.force_authenticate(user=self.district_admin)
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation_with_bed.external_id}/daily_rounds/",
            data=self.log_update,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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

    def test_doctors_log_update(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation_with_bed.external_id}/daily_rounds/",
            data={**self.log_update, "rounds_type": "DOCTORS_LOG"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_community_nurses_log_update(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation_with_bed.external_id}/daily_rounds/",
            data={
                **self.log_update,
                "rounds_type": "COMMUNITY_NURSES_LOG",
                "bowel_issue": "NO_DIFFICULTY",
                "bladder_drainage": "CONDOM_CATHETER",
                "bladder_issue": "NO_ISSUES",
                "urination_frequency": "DECREASED",
                "sleep": "SATISFACTORY",
                "nutrition_route": "ORAL",
                "oral_issue": "NO_ISSUE",
                "appetite": "INCREASED",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_taken_at(self):
        data = {
            **self.log_update,
            "taken_at": timezone.now() + timedelta(minutes=5),
        }
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation_with_bed.external_id}/daily_rounds/",
            data,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
