import datetime
from unittest.mock import patch

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.api.serializers.patient_consultation import MIN_ENCOUNTER_DATE
from care.facility.models.file_upload import FileUpload
from care.facility.models.icd11_diagnosis import (
    ConditionVerificationStatus,
    ICD11Diagnosis,
)
from care.facility.models.patient_base import NewDischargeReasonEnum, SuggestionChoices
from care.facility.models.patient_consultation import (
    CATEGORY_CHOICES,
    PatientConsultation,
)
from care.utils.tests.test_utils import TestUtils


class TestPatientConsultation(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.location = cls.create_asset_location(cls.facility)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.doctor = cls.create_user(
            "doctor", cls.district, home_facility=cls.facility, user_type=15
        )
        cls.patient1 = cls.create_patient(cls.district, cls.facility)

    def get_default_data(self):
        return {
            "route_to_facility": 10,
            "symptoms": [1],
            "category": CATEGORY_CHOICES[0][0],
            "examination_details": "examination_details",
            "history_of_present_illness": "history_of_present_illness",
            "treatment_plan": "treatment_plan",
            "suggestion": SuggestionChoices.HI,
            "treating_physician": self.doctor.id,
            "create_diagnoses": [
                {
                    "diagnosis": ICD11Diagnosis.objects.first().id,
                    "is_principal": False,
                    "verification_status": ConditionVerificationStatus.CONFIRMED,
                }
            ],
            "patient_no": datetime.datetime.now().timestamp(),
        }

    def get_url(self, consultation=None):
        if consultation:
            return f"/api/v1/consultation/{consultation.external_id}/"
        return "/api/v1/consultation/"

    def create_route_to_facility_consultation(
        self, patient=None, route_to_facility=10, **kwargs
    ):
        patient = patient or self.create_patient(self.district, self.facility)
        data = self.get_default_data().copy()
        kwargs.update(
            {
                "patient": patient.external_id,
                "facility": self.facility.external_id,
                "route_to_facility": route_to_facility,
            }
        )
        data.update(kwargs)
        return self.client.post(self.get_url(), data, format="json")

    def create_admission_consultation(self, patient=None, **kwargs):
        patient = patient or self.create_patient(self.district, self.facility)
        data = self.get_default_data().copy()
        kwargs.update(
            {
                "patient": patient.external_id,
                "facility": self.facility.external_id,
            }
        )
        data.update(kwargs)
        res = self.client.post(self.get_url(), data, format="json")
        return PatientConsultation.objects.get(external_id=res.data["id"])

    def update_consultation(self, consultation, **kwargs):
        return self.client.patch(self.get_url(consultation), kwargs, "json")

    def add_diagnosis(self, consultation, **kwargs):
        return self.client.post(
            f"{self.get_url(consultation)}diagnoses/", kwargs, "json"
        )

    def edit_diagnosis(self, consultation, id, **kwargs):
        return self.client.patch(
            f"{self.get_url(consultation)}diagnoses/{id}/", kwargs, "json"
        )

    def discharge(self, consultation, **kwargs):
        return self.client.post(
            f"{self.get_url(consultation)}discharge_patient/", kwargs, "json"
        )

    def test_encounter_date_less_than_minimum(self):
        date = MIN_ENCOUNTER_DATE - datetime.timedelta(days=1)
        patient = self.create_patient(self.district, self.facility)
        data = self.get_default_data().copy()
        data.update(
            {
                "patient": patient.external_id,
                "facility": self.facility.external_id,
                "encounter_date": date,
            }
        )
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_consultation_treating_physician_invalid_user(self):
        consultation = self.create_admission_consultation(suggestion="A")
        res = self.update_consultation(
            consultation, treating_physician=self.user.id, suggestion="A"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_preadmission(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
            discharge_date="2002-04-01T16:30:00Z",
            discharge_notes="Discharge as recovered before admission",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_future(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
            discharge_date="2319-04-01T15:30:00Z",
            discharge_notes="Discharge as recovered in the future",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_after_admission(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
            discharge_date="2020-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered after admission before future",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_discharge_as_expired_pre_admission(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.EXPIRED,
            death_datetime="2002-04-01T16:30:00Z",
            discharge_notes="Death before admission",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_future(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.EXPIRED,
            death_datetime="2319-04-01T15:30:00Z",
            discharge_notes="Death in the future",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_after_admission(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.EXPIRED,
            death_datetime="2020-04-02T15:30:00Z",
            discharge_notes="Death after admission before future",
            death_confirmed_doctor="Dr. Test",
            discharge_date="2319-04-01T15:30:00Z",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_discharge_as_recovered_with_expired_fields(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2023, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
            discharge_date="2023-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered with expired fields",
            death_datetime="2023-04-02T15:30:00Z",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        consultation.refresh_from_db()
        self.assertIsNone(consultation.death_datetime)
        self.assertIsNot(consultation.death_confirmed_doctor, "Dr. Test")

    def discharge_summary(self, consultation, **kwargs):
        return self.client.post(
            f"{self.get_url(consultation)}generate_discharge_summary/", kwargs, "json"
        )

    def test_discharge_summary(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        with patch.object(FileUpload, "put_object"):
            self.discharge_summary(
                consultation,
                new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
                discharge_date="2020-04-02T15:30:00Z",
                discharge_notes="Discharge as recovered after admission before future",
            )

        file_res = FileUpload.objects.filter(
            associating_id=consultation.external_id,
            upload_completed=True,
            is_archived=False,
        )
        uploaded_file = file_res[0]
        self.assertFalse(uploaded_file.name.endswith(".pdf"))

    def test_referred_to_external_null(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.REFERRED,
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with null referred_to_external",
            referred_to_external=None,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_external_empty_string(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.REFERRED,
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with empty referred_to_external",
            referred_to_external="",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_empty_facility(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.REFERRED,
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with empty referred_to_external",
            referred_to=None,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_and_external_together(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.REFERRED,
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with null referred_to_external",
            referred_to_external="External Facility",
            referred_to=self.facility.external_id,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_referred_to_valid_value(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        referred_to_external = "Test Hospital"
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.REFERRED,
            discharge_date="2023-07-01T12:00:00Z",
            referred_to_external=referred_to_external,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_external_valid_value(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        referred_to_external = "Test Hospital"
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.REFERRED,
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with valid referred_to_external",
            referred_to_external=referred_to_external,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_route_to_facility_referred_from_facility_empty(self):
        res = self.create_route_to_facility_consultation(route_to_facility=20)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_route_to_facility_referred_from_facility_external(self):
        res = self.create_route_to_facility_consultation(
            route_to_facility=20, referred_from_facility_external="Test"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_route_to_facility_referred_from_facility(self):
        res = self.create_route_to_facility_consultation(
            route_to_facility=20, referred_from_facility=self.facility.external_id
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_route_to_facility_referred_from_facility_and_external_together(self):
        res = self.create_route_to_facility_consultation(
            route_to_facility=20,
            referred_from_facility="123",
            referred_from_facility_external="Test",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_route_to_facility_transfer_within_facility_empty(self):
        res = self.create_route_to_facility_consultation(route_to_facility=30)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_route_to_facility_transfer_within_facility(self):
        res = self.create_route_to_facility_consultation(
            route_to_facility=30, transferred_from_location=self.location.external_id
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_medico_legal_case(self):
        consultation = self.create_admission_consultation(
            medico_legal_case=True,
            encounter_date=make_aware(datetime.datetime(2023, 4, 1, 15, 30, 00)),
        )
        url = self.get_url(consultation)

        data = self.client.get(url)
        self.assertEqual(data.status_code, status.HTTP_200_OK)
        self.assertEqual(data.data["medico_legal_case"], True)

        # Test Patch
        response = self.update_consultation(consultation, medico_legal_case=False)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["medico_legal_case"], False)

        # Test Patch after discharge
        response = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with valid referred_to_external",
            medico_legal_case=False,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = self.client.get(url)
        self.assertEqual(data.status_code, status.HTTP_200_OK)
        self.assertEqual(data.data["medico_legal_case"], False)

        response = self.update_consultation(consultation, medico_legal_case=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["medico_legal_case"], True)

    def test_update_consultation_after_discharge(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
            discharge_date="2020-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered after admission before future",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.update_consultation(
            consultation, symptoms=[1, 2], category="MILD", suggestion="A"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_diagnoses_and_duplicate_diagnoses(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        diagnosis = ICD11Diagnosis.objects.all()[0].id
        res = self.add_diagnosis(
            consultation,
            diagnosis=diagnosis,
            is_principal=True,
            verification_status=ConditionVerificationStatus.CONFIRMED,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.add_diagnosis(
            consultation,
            diagnosis=diagnosis,
            is_principal=True,
            verification_status=ConditionVerificationStatus.PROVISIONAL,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_diagnosis_inactive(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        diagnosis = ICD11Diagnosis.objects.first().id
        res = self.add_diagnosis(
            consultation,
            diagnosis=diagnosis,
            is_principal=False,
            verification_status=ConditionVerificationStatus.ENTERED_IN_ERROR,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.add_diagnosis(
            consultation,
            diagnosis=diagnosis,
            is_principal=True,
            verification_status=ConditionVerificationStatus.REFUTED,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def mark_inactive_diagnosis_as_principal(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        diagnosis = ICD11Diagnosis.objects.first().id
        res = self.add_diagnosis(
            consultation,
            diagnosis=diagnosis,
            is_principal=False,
            verification_status=ConditionVerificationStatus.CONFIRMED,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.edit_diagnosis(
            consultation,
            res.data["id"],
            verification_status=ConditionVerificationStatus.REFUTED,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.edit_diagnosis(
            consultation,
            res.data["id"],
            is_principal=True,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_diagnosis(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.add_diagnosis(
            consultation,
            diagnosis=ICD11Diagnosis.objects.all()[0].id,
            is_principal=False,
            verification_status=ConditionVerificationStatus.CONFIRMED,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.edit_diagnosis(
            consultation,
            res.data["id"],
            diagnosis=ICD11Diagnosis.objects.all()[1].id,
            is_principal=True,
            verification_status=ConditionVerificationStatus.PROVISIONAL,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_multiple_principal_diagnosis(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.add_diagnosis(
            consultation,
            diagnosis=ICD11Diagnosis.objects.all()[0].id,
            is_principal=True,
            verification_status=ConditionVerificationStatus.CONFIRMED,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.add_diagnosis(
            consultation,
            diagnosis=ICD11Diagnosis.objects.all()[1].id,
            is_principal=True,
            verification_status=ConditionVerificationStatus.PROVISIONAL,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_principal_edit_as_inactive_add_principal(self):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.add_diagnosis(
            consultation,
            diagnosis=ICD11Diagnosis.objects.all()[0].id,
            is_principal=True,
            verification_status=ConditionVerificationStatus.CONFIRMED,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.edit_diagnosis(
            consultation,
            res.data["id"],
            verification_status=ConditionVerificationStatus.ENTERED_IN_ERROR,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["is_principal"])
        res = self.add_diagnosis(
            consultation,
            diagnosis=ICD11Diagnosis.objects.all()[1].id,
            is_principal=True,
            verification_status=ConditionVerificationStatus.PROVISIONAL,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_consultations_with_duplicate_patient_no_within_facility(self):
        patient2 = self.create_patient(self.district, self.facility)
        data = self.get_default_data().copy()
        data.update(
            {
                "patient_no": "IP1234",
                "patient": patient2.external_id,
                "facility": self.facility.external_id,
                "created_by": self.user.external_id,
                "suggestion": SuggestionChoices.A,
            }
        )
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        data.update(
            {
                "patient_no": "IP1234",
                "patient": self.patient1.external_id,
                "facility": self.facility.external_id,
                "created_by": self.user.external_id,
            }
        )
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        data.update({"suggestion": SuggestionChoices.A})
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_consultations_with_same_patient_no_in_different_facilities(self):
        facility2 = self.create_facility(
            self.super_user, self.district, self.local_body, name="bar"
        )
        patient2 = self.create_patient(self.district, facility2)
        doctor2 = self.create_user(
            "doctor2", self.district, home_facility=facility2, user_type=15
        )
        data = self.get_default_data().copy()
        data.update(
            {
                "patient_no": "IP1234",
                "patient": self.patient1.external_id,
                "created_by": self.user.external_id,
                "suggestion": SuggestionChoices.A,
            }
        )
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data.update(
            {
                "patient_no": "IP1234",
                "patient": patient2.external_id,
                "created_by": self.user.external_id,
                "suggestion": SuggestionChoices.A,
                "treating_physician": doctor2.id,
            }
        )
        self.client.force_authenticate(user=doctor2)
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_patient_was_discharged_and_then_added_with_a_different_patient_number(
        self,
    ):
        consultation = self.create_admission_consultation(
            suggestion=SuggestionChoices.A,
            encounter_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
            patient=self.patient1,
        )
        res = self.discharge(
            consultation,
            new_discharge_reason=NewDischargeReasonEnum.RECOVERED,
            discharge_date="2020-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered after admission before future",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = self.get_default_data().copy()
        data.update(
            {
                "patient_no": "IP1234",
                "patient": self.patient1.external_id,
                "created_by": self.user.external_id,
                "suggestion": SuggestionChoices.A,
            }
        )
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_allow_empty_op_no(self):
        data = self.get_default_data().copy()
        data.update(
            {
                "patient_no": "",
                "patient": self.patient1.external_id,
                "created_by": self.user.external_id,
                "suggestion": SuggestionChoices.OP,
            }
        )
        res = self.client.post(self.get_url(), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
