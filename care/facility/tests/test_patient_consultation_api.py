import datetime

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.patient_consultation import PatientConsultationViewSet
from care.facility.models.patient_consultation import (
    CATEGORY_CHOICES,
    PatientConsultation,
)
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class TestPatientConsultation(TestBase, TestClassMixin, APITestCase):
    default_data = {
        "symptoms": [1],
        "category": CATEGORY_CHOICES[0][0],
        "examination_details": "examination_details",
        "history_of_present_illness": "history_of_present_illness",
        "prescribed_medication": "prescribed_medication",
        "suggestion": PatientConsultation.SUGGESTION_CHOICES[0][0],
    }

    def setUp(self):
        self.factory = APIRequestFactory()
        self.consultation = self.create_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )

    def create_admission_consultation(self, patient=None, **kwargs):
        patient = (
            self.create_patient(facility_id=self.facility.id)
            if not patient
            else patient
        )
        data = self.default_data.copy()
        kwargs.update(
            {
                "patient": patient.external_id,
                "facility": self.facility.external_id,
            }
        )
        data.update(kwargs)
        res = self.new_request(
            (self.get_url(), data, "json"),
            {"post": "create"},
            PatientConsultationViewSet,
            self.state_admin,
            {},
        )
        return PatientConsultation.objects.get(external_id=res.data["id"])

    def get_url(self, consultation=None):
        if consultation:
            return f"/api/v1/consultation/{consultation.external_id}"
        return "/api/v1/consultation"

    def discharge(self, consultation, **kwargs):
        return self.new_request(
            (f"{self.get_url(consultation)}/discharge_patient", kwargs, "json"),
            {"post": "discharge_patient"},
            PatientConsultationViewSet,
            self.state_admin,
            {"external_id": consultation.external_id},
        )

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
