import datetime

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APITestCase

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
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.doctor = cls.create_user(
            "doctor", cls.district, home_facility=cls.facility, user_type=15,
        )

    def get_default_data(self):
        return {
            "symptoms": [1],
            "category": CATEGORY_CHOICES[0][0],
            "examination_details": "examination_details",
            "history_of_present_illness": "history_of_present_illness",
            "treatment_plan": "treatment_plan",
            "suggestion": PatientConsultation.SUGGESTION_CHOICES[0][0],
            "verified_by": self.doctor.id,
        }

    def get_url(self, consultation=None):
        if consultation:
            return f"/api/v1/consultation/{consultation.external_id}/"
        return "/api/v1/consultation/"

    def create_admission_consultation(self, patient=None, **kwargs):
        patient = patient or self.create_patient(self.district, self.facility)
        data = self.get_default_data().copy()
        kwargs.update(
            {
                "patient": patient.external_id,
                "facility": self.facility.external_id,
            },
        )
        data.update(kwargs)
        res = self.client.post(self.get_url(), data)
        return PatientConsultation.objects.get(external_id=res.data["id"])

    def update_consultation(self, consultation, **kwargs):
        return self.client.patch(self.get_url(consultation), kwargs, "json")

    def discharge(self, consultation, **kwargs):
        return self.client.post(
            f"{self.get_url(consultation)}discharge_patient/", kwargs, "json",
        )

    def test_create_consultation_verified_by_invalid_user(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.update_consultation(
            consultation, verified_by=self.doctor.id, suggestion="A",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_preadmission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2002-04-01T16:30:00Z",
            discharge_notes="Discharge as recovered before admission",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_future(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2319-04-01T15:30:00Z",
            discharge_notes="Discharge as recovered in the future",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_after_admission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2020-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered after admission before future",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_discharge_as_expired_pre_admission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="EXP",
            death_datetime="2002-04-01T16:30:00Z",
            discharge_notes="Death before admission",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_future(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="EXP",
            death_datetime="2319-04-01T15:30:00Z",
            discharge_notes="Death in the future",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_after_admission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="EXP",
            death_datetime="2020-04-02T15:30:00Z",
            discharge_notes="Death after admission before future",
            death_confirmed_doctor="Dr. Test",
            discharge_date="2319-04-01T15:30:00Z",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_discharge_as_recovered_with_expired_fields(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2023, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2023-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered with expired fields",
            death_datetime="2023-04-02T15:30:00Z",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        consultation.refresh_from_db()
        self.assertIsNone(consultation.death_datetime)
        self.assertIsNot(consultation.death_confirmed_doctor, "Dr. Test")

    def test_referred_to_external_null(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with null referred_to_external",
            referred_to_external=None,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_external_empty_string(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with empty referred_to_external",
            referred_to_external="",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_empty_facility(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with empty referred_to_external",
            referred_to=None,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_and_external_together(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with null referred_to_external",
            referred_to_external="External Facility",
            referred_to=self.facility.external_id,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_referred_to_valid_value(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        referred_to_external = "Test Hospital"
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            referred_to_external=referred_to_external,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_external_valid_value(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        referred_to_external = "Test Hospital"
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with valid referred_to_external",
            referred_to_external=referred_to_external,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
