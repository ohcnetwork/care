import datetime

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models.patient_base import NewDischargeReasonEnum
from care.utils.tests.test_utils import TestUtils


class TestPatientConsultationAccess(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        # Variables named in the perspective of reader being a member of the home facility
        cls.home_facility = cls.create_facility(
            cls.super_user, cls.district, cls.local_body, name="Home Facility"
        )
        cls.remote_facility = cls.create_facility(
            cls.super_user, cls.district, cls.local_body, name="Remote Facility"
        )
        cls.facility = cls.remote_facility
        cls.unrelated_facility = cls.create_facility(
            cls.super_user, cls.district, cls.local_body, name="Unreleated Facility"
        )
        cls.home_doctor = cls.create_user(
            "home-doctor",
            cls.district,
            home_facility=cls.home_facility,
            user_type=15,
        )
        cls.user = cls.home_doctor
        cls.remote_doctor = cls.create_user(
            "remote-doctor",
            cls.district,
            home_facility=cls.remote_facility,
            user_type=15,
        )
        # remote doctor has access to the my home facility
        cls.link_user_with_facility(
            cls.remote_doctor, cls.home_facility, created_by=cls.super_user
        )
        # this doctor has no idea about whats going to happen.
        cls.unrelated_doctor = cls.create_user(
            "unrelated-doctor",
            cls.district,
            home_facility=cls.unrelated_facility,
            user_type=15,
        )
        cls.patient = cls.create_patient(cls.district, cls.remote_facility)
        cls.patient1 = cls.create_patient(cls.district, cls.remote_facility)

    def list_patients(self, **kwargs):
        return self.client.get("/api/v1/patient/", data=kwargs)

    def retrieve_patient(self, patient):
        return self.client.get(f"/api/v1/patient/{patient.external_id}/")

    def retieve_patient_consultations(self, patient):
        return self.client.get(
            "/api/v1/consultation/", data={"patient": patient.external_id}
        )

    def retrieve_discharged_patients_of_facility(self, facility):
        return self.client.get(
            f"/api/v1/facility/{facility.external_id}/discharged_patients/"
        )

    def discharge(self, consultation, **kwargs):
        return self.client.post(
            f"/api/v1/consultation/{consultation.external_id}/discharge_patient/",
            data={
                "new_discharge_reason": NewDischargeReasonEnum.RECOVERED,
                **kwargs,
            },
            format="json",
        )

    def test_discharge_patient_ordering_filter(self):
        consultation1 = self.create_consultation(
            self.patient,
            self.home_facility,
            suggestion="A",
            encounter_date=make_aware(datetime.datetime(2024, 1, 3)),
        )
        consultation2 = self.create_consultation(
            self.patient1,
            self.home_facility,
            suggestion="A",
            encounter_date=make_aware(datetime.datetime(2024, 1, 1)),
        )
        self.discharge(consultation1, discharge_date="2024-01-04T00:00:00Z")
        self.discharge(consultation2, discharge_date="2024-01-02T00:00:00Z")

        # order by reverse modified date
        patients_order = [self.patient1, self.patient]
        response = self.client.get(
            f"/api/v1/facility/{self.home_facility.external_id}/discharged_patients/?ordering=-modified_date",
        )
        response = response.json()["results"]
        for i in range(len(response)):
            self.assertEqual(str(patients_order[i].external_id), response[i]["id"])

        # order by modified date
        patients_order.reverse()
        response = self.client.get(
            f"/api/v1/facility/{self.home_facility.external_id}/discharged_patients/?ordering=modified_date",
        )
        response = response.json()["results"]
        for i in range(len(response)):
            self.assertEqual(str(patients_order[i].external_id), response[i]["id"])

    def test_patient_consultation_access(self):  # noqa: PLR0915
        # In this test, a patient is admitted to a remote facility and then later admitted to a home facility.

        # Admit patient to the remote facility
        remote_consultation = self.create_consultation(
            self.patient,
            self.remote_facility,
            suggestion="A",
            encounter_date=make_aware(datetime.datetime(2024, 1, 1)),
        )

        # Permission Check: Remote doctor must have access to the patient details and the current consultation
        self.client.force_authenticate(user=self.remote_doctor)
        res = self.retrieve_discharged_patients_of_facility(self.remote_facility)
        self.assertNotContains(res, self.patient.external_id)
        res = self.list_patients(
            is_active="true", ordering="-last_consultation__current_bed__bed__name"
        )
        self.assertContains(res, self.patient.external_id)
        res = self.retrieve_patient(self.patient)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.retieve_patient_consultations(self.patient)
        self.assertContains(res, remote_consultation.external_id)

        # Home doctor must NOT have access to this facility.
        # Also should not have access to the patient or consultation at present.
        self.client.force_authenticate(user=self.home_doctor)
        res = self.retrieve_patient(self.patient)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        res = self.retieve_patient_consultations(self.patient)
        self.assertNotContains(res, remote_consultation.external_id)

        # Unrelated doctor must NOT have access
        self.client.force_authenticate(user=self.unrelated_doctor)
        res = self.retrieve_patient(self.patient)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        res = self.retieve_patient_consultations(self.patient)
        self.assertNotContains(res, remote_consultation.external_id)

        # Discharge the patient from remote facility.
        self.client.force_authenticate(user=self.remote_doctor)
        res = self.discharge(remote_consultation, discharge_date="2024-01-02T00:00:00Z")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.list_patients(is_active="true", ordering="created_date")
        self.assertNotContains(res, self.patient.external_id)
        res = self.list_patients(
            is_active="false", ordering="-last_consultation__current_bed__bed__name"
        )
        self.assertContains(res, self.patient.external_id)

        # Admit to home facility
        self.client.force_authenticate(user=self.home_doctor)
        home_consultation = self.create_consultation(
            self.patient,
            self.home_facility,
            suggestion="A",
            encounter_date=make_aware(datetime.datetime(2024, 1, 3)),
        )

        # Remote doctor must have access to patient and remote_consultation and home_consultation
        self.client.force_authenticate(user=self.remote_doctor)
        res = self.retrieve_discharged_patients_of_facility(self.remote_facility)
        self.assertContains(res, self.patient.external_id)
        res = self.retrieve_patient(self.patient)
        res = self.list_patients(is_active="true", ordering="-category_severity")
        self.assertContains(res, self.patient.external_id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.retieve_patient_consultations(self.patient)
        self.assertContains(res, remote_consultation.external_id)
        self.assertContains(res, home_consultation.external_id)

        # Home doctor should have access to the patient and all past and current consultation
        self.client.force_authenticate(user=self.home_doctor)
        res = self.retrieve_patient(self.patient)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.retieve_patient_consultations(self.patient)
        self.assertContains(res, home_consultation.external_id)
        self.assertContains(res, remote_consultation.external_id)

        # Discharge the patient from home facility.
        res = self.discharge(home_consultation, discharge_date="2024-01-04T00:00:00Z")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.list_patients(is_active="false", ordering="name")
        self.assertContains(res, self.patient.external_id)
        res = self.retrieve_discharged_patients_of_facility(self.home_facility)
        self.assertContains(res, self.patient.external_id)
        self.assertContains(res, home_consultation.external_id)
        self.assertNotContains(res, remote_consultation.external_id)

        # Now remote doctor should have access to the patient and the remote consultation, but not home consultation
        self.client.force_authenticate(user=self.remote_doctor)
        res = self.retrieve_discharged_patients_of_facility(self.remote_facility)
        self.assertContains(res, self.patient.external_id)
        res = self.retieve_patient_consultations(self.patient)
        self.assertContains(res, remote_consultation.external_id)
        self.assertNotContains(res, home_consultation.external_id)
