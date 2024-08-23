from datetime import timedelta

from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models.encounter_symptom import (
    ClinicalImpressionStatus,
    EncounterSymptom,
    Symptom,
)
from care.facility.models.icd11_diagnosis import (
    ConditionVerificationStatus,
    ICD11Diagnosis,
)
from care.utils.tests.test_utils import TestUtils


class TestEncounterSymptomInConsultation(TestUtils, APITestCase):
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
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.consultation_data = cls.get_consultation_data()
        cls.consultation_data.update(
            {
                "patient": cls.patient.external_id,
                "consultation": cls.facility.external_id,
                "treating_physician": cls.doctor.id,
                "create_diagnoses": [
                    {
                        "diagnosis": ICD11Diagnosis.objects.first().id,
                        "is_principal": False,
                        "verification_status": ConditionVerificationStatus.CONFIRMED,
                    }
                ],
                "create_symptoms": [
                    {
                        "symptom": Symptom.COUGH,
                        "onset_date": now(),
                    },
                    {
                        "symptom": Symptom.FEVER,
                        "onset_date": now(),
                    },
                ],
            }
        )

    def test_create_consultation(self):
        data = self.consultation_data.copy()

        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EncounterSymptom.objects.count(), 2)

    def test_create_consultation_with_duplicate_symptoms(self):
        data = self.consultation_data.copy()
        data["create_symptoms"] = [
            {
                "symptom": Symptom.FEVER,
                "onset_date": now(),
            },
            {
                "symptom": Symptom.FEVER,
                "onset_date": now(),
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"create_symptoms": ["Duplicate symptoms are not allowed"]},
        )

        data["create_symptoms"] = [
            {
                "symptom": Symptom.OTHERS,
                "other_symptom": "Other Symptom",
                "onset_date": now(),
            },
            {
                "symptom": Symptom.OTHERS,
                "other_symptom": "Other Symptom",
                "onset_date": now(),
            },
        ]

        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"create_symptoms": ["Duplicate symptoms are not allowed"]},
        )

    def test_create_consultation_with_duplicate_cured_symptoms(self):
        data = self.consultation_data.copy()
        data["create_symptoms"] = [
            {
                "symptom": Symptom.FEVER,
                "onset_date": now(),
                "cure_date": now(),
            },
            {
                "symptom": Symptom.FEVER,
                "onset_date": now(),
            },
            {
                "symptom": Symptom.OTHERS,
                "other_symptom": "Other Symptom",
                "onset_date": now(),
                "cure_date": now(),
            },
            {
                "symptom": Symptom.OTHERS,
                "other_symptom": "Other Symptom",
                "onset_date": now(),
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_consultation_with_no_symptom(self):
        data = self.consultation_data.copy()

        data["create_symptoms"] = []
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EncounterSymptom.objects.count(), 0)

    def test_create_consultation_with_invalid_symptom(self):
        data = self.consultation_data.copy()
        data["create_symptoms"] = [
            {
                "symptom": 100,
                "onset_date": now(),
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"create_symptoms": [{"symptom": ['"100" is not a valid choice.']}]},
        )

        data["create_symptoms"] = [
            {
                "symptom": Symptom.OTHERS,
                "onset_date": now(),
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "create_symptoms": {
                    "other_symptom": "Other symptom should not be empty when symptom type is OTHERS"
                }
            },
        )

    def test_create_consultation_with_no_symptom_onset_date(self):
        data = self.consultation_data.copy()
        data["create_symptoms"] = [
            {
                "symptom": Symptom.FEVER,
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"create_symptoms": [{"onset_date": ["This field is required."]}]},
        )

    def test_create_consultation_with_symptom_onset_date_in_future(self):
        data = self.consultation_data.copy()
        data["create_symptoms"] = [
            {
                "symptom": Symptom.FEVER,
                "onset_date": now() + timedelta(days=1),
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"create_symptoms": {"onset_date": "Onset date cannot be in the future"}},
        )

    def test_create_consultation_with_cure_date_before_onset_date(self):
        data = self.consultation_data.copy()
        data["create_symptoms"] = [
            {
                "symptom": Symptom.FEVER,
                "onset_date": now(),
                "cure_date": now() - timedelta(days=1),
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"create_symptoms": {"cure_date": "Cure date should be after onset date"}},
        )

    def test_create_consultation_with_correct_cure_date(self):
        data = self.consultation_data.copy()
        data["create_symptoms"] = [
            {
                "symptom": Symptom.FEVER,
                "onset_date": now() - timedelta(days=1),
                "cure_date": now(),
            },
        ]
        response = self.client.post(
            "/api/v1/consultation/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EncounterSymptom.objects.count(), 1)
        self.assertEqual(
            EncounterSymptom.objects.first().clinical_impression_status,
            ClinicalImpressionStatus.COMPLETED,
        )


class TestEncounterSymptomApi(TestUtils, APITestCase):
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
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.consultation = cls.create_consultation(
            cls.patient, cls.facility, cls.doctor
        )

    def get_url(self, symptom=None):
        if symptom:
            return f"/api/v1/consultation/{self.consultation.external_id}/symptoms/{symptom.external_id}/"
        return f"/api/v1/consultation/{self.consultation.external_id}/symptoms/"

    def test_create_new_symptom(self):
        data = {
            "symptom": Symptom.FEVER,
            "onset_date": now(),
        }
        response = self.client.post(
            self.get_url(),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EncounterSymptom.objects.count(), 1)

    def test_create_static_symptom_with_other_symptom(self):
        data = {
            "symptom": Symptom.FEVER,
            "other_symptom": "Other Symptom",
            "onset_date": now(),
        }
        response = self.client.post(
            self.get_url(),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "other_symptom": [
                    "Other symptom should be empty when symptom type is not OTHERS"
                ]
            },
        )

    def test_create_others_symptom(self):
        data = {
            "symptom": Symptom.OTHERS,
            "other_symptom": "Other Symptom",
            "onset_date": now(),
        }
        response = self.client.post(
            self.get_url(),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EncounterSymptom.objects.count(), 1)

    def test_create_other_symptom_without_other_symptom(self):
        data = {
            "symptom": Symptom.OTHERS,
            "onset_date": now(),
        }
        response = self.client.post(
            self.get_url(),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "other_symptom": [
                    "Other symptom should not be empty when symptom type is OTHERS"
                ]
            },
        )

    def test_create_duplicate_symptoms(self):
        EncounterSymptom.objects.create(
            consultation=self.consultation,
            symptom=Symptom.FEVER,
            onset_date=now(),
            created_by=self.user,
        )
        data = {
            "symptom": Symptom.FEVER,
            "onset_date": now(),
        }
        response = self.client.post(
            self.get_url(),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"symptom": ["An active symptom with the same details already exists"]},
        )

    def test_update_symptom(self):
        symptom = EncounterSymptom.objects.create(
            consultation=self.consultation,
            symptom=Symptom.FEVER,
            onset_date=now(),
            created_by=self.user,
        )
        data = {
            "cure_date": now(),
        }
        response = self.client.patch(
            self.get_url(symptom),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(EncounterSymptom.objects.count(), 1)

    def test_create_onset_date_in_future(self):
        data = {
            "symptom": Symptom.FEVER,
            "onset_date": now() + timedelta(days=1),
        }
        response = self.client.post(
            self.get_url(),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"onset_date": ["Onset date cannot be in the future"]},
        )

    def test_cure_date_before_onset_date(self):
        symptom = EncounterSymptom.objects.create(
            consultation=self.consultation,
            symptom=Symptom.FEVER,
            onset_date=now(),
            created_by=self.user,
        )
        data = {
            "cure_date": now() - timedelta(days=1),
        }
        response = self.client.patch(
            self.get_url(symptom),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"cure_date": ["Cure date should be after onset date"]},
        )

    def test_mark_symptom_as_error(self):
        symptom = EncounterSymptom.objects.create(
            consultation=self.consultation,
            symptom=Symptom.FEVER,
            onset_date=now(),
            created_by=self.user,
        )
        response = self.client.delete(
            self.get_url(symptom),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            EncounterSymptom.objects.get(id=symptom.id).clinical_impression_status,
            ClinicalImpressionStatus.ENTERED_IN_ERROR,
        )
