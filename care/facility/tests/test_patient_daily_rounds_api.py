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
            "taken_at": timezone.now().isoformat(),
        }

    def get_url(self, external_consultation_id=None):
        return f"/api/v1/consultation/{external_consultation_id}/daily_rounds/analyse/"

    def create_log_update(self, **kwargs):
        consultation = kwargs.pop("consultation", self.consultation_with_bed)
        return self.client.post(
            f"/api/v1/consultation/{consultation.external_id}/daily_rounds/",
            data={**self.log_update, **kwargs},
            format="json",
        )

    def test_external_consultation_does_not_exists_returns_404(self):
        sample_uuid = "e4a3d84a-d678-4992-9287-114f029046d8"
        response = self.client.get(self.get_url(sample_uuid))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_action_in_log_update(self):
        response = self.create_log_update(consultation=self.consultation_with_bed)
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

    def test_log_update_without_bed_for_admission(self):
        response = self.create_log_update(
            consultation=self.admission_consultation_no_bed
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["bed"],
            "Patient does not have a bed assigned. Please assign a bed first",
        )

    def test_log_update_without_bed_for_domiciliary(self):
        response = self.create_log_update(
            consultation=self.domiciliary_consultation_no_bed
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_doctors_log_update(self):
        response = self.create_log_update(rounds_type="DOCTORS_LOG")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_log_update_with_blood_pressure_empty(self):
        response = self.create_log_update(bp={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_partial_blood_pressure(self):
        response = self.create_log_update(bp={"systolic": 60})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_out_of_range_blood_pressure(self):
        response = self.create_log_update(bp={"systolic": 1000, "diastolic": 60})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_systolic_below_diastolic_blood_pressure(self):
        response = self.create_log_update(
            bp={"systolic": 60, "diastolic": 90},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_valid_blood_pressure(self):
        response = self.create_log_update(
            bp={"systolic": 90, "diastolic": 60},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_log_update_with_incorrect_infusion_name(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            infusions=[{"name": "", "quantity": 1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_infusions_quantity_out_of_range(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            infusions=[{"name": "Adrenalin", "quantity": -1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_valid_infusions(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            infusions=[{"name": "Adrenalin", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_log_update_with_incorrect_iv_fluids_name(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            iv_fluids=[{"name": "", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_iv_fluids_quantity_out_of_range(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            iv_fluids=[{"name": "RL", "quantity": -1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_valid_iv_fluids(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            iv_fluids=[{"name": "RL", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_log_update_with_incorrect_feeds_name(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            feeds=[{"name": "", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_feeds_quantity_out_of_range(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            feeds=[{"name": "Ryles Tube", "quantity": -1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_valid_feeds(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            feeds=[{"name": "Ryles Tube", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_log_update_with_incorrect_output_name(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[{"name": "", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_output_quantity_out_of_range(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[{"name": "Abdominal Drain", "quantity": -1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_log_update_with_valid_output(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[{"name": "Abdominal Drain", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_log_update_with_incorrect_nursing_procedure(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[{"name": "Abdominal Drain", "quantity": 10}],
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_pressure_sore_with_invalid_region(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[
                {
                    "region": "",
                    "length": 1,
                    "width": 1,
                }
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pressure_sore_with_length_out_of_range(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[{"region": "PosteriorNeck", "length": -10, "width": 1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pressure_sore_with_width_out_of_range(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[{"region": "PosteriorNeck", "length": 1, "width": -1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pressure_sore_with_missing_region(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[{"length": 1, "width": -1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pressure_sore_with_invalid_exudate_amount(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[
                {
                    "region": "PosteriorNeck",
                    "length": 1,
                    "width": 1,
                    "exudate_amount": "",
                }
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pressure_sore_with_invalid_tissue_type(self):
        response = self.create_log_update(
            rounds_type="VENTILATOR",
            output=[
                {
                    "region": "PosteriorNeck",
                    "length": 1,
                    "width": 1,
                    "tissue_type": "Closed",
                }
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
