import datetime

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from care.facility.api.viewsets.patient_consultation import PatientConsultationViewSet
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class TestPatientConsultation(TestBase, TestClassMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.consultation = self.create_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )

    def get_url(self):
        return f"/api/v1/consultation/{self.consultation.external_id}"

    def discharge_patient(self, **kwargs):
        return self.new_request(
            (f"{self.get_url()}/discharge_patient", kwargs, "json"),
            {"post": "discharge_patient"},
            PatientConsultationViewSet,
            self.user,
            {"external_id": self.consultation.external_id},
        )

    def test_discharge_as_recovered_preadmission(self):
        response = self.discharge_patient(
            discharge_reason="REC",
            discharge_date="2002-04-01T16:30:00Z",
            discharge_notes="Recovery being tested",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_future(self):
        response = self.discharge_patient(
            discharge_reason="REC",
            discharge_date="2319-04-01T15:30:00Z",
            discharge_notes="Recovery being tested",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_preadmission(self):
        response = self.discharge_patient(
            discharge_reason="EXP",
            death_datetime="2002-04-01T16:30:00Z",
            discharge_notes="Death before admission being tested",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_future(self):
        response = self.discharge_patient(
            discharge_reason="EXP",
            death_datetime="2319-04-01T15:30:00Z",
            discharge_notes="Future death being tested",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired(self):
        response = self.discharge_patient(
            discharge_reason="EXP",
            death_datetime="2020-04-02T15:30:00Z",
            discharge_notes="Death being tested",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
