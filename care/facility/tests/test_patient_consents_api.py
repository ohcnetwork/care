from rest_framework.test import APITestCase

from care.facility.models.patient_consultation import ConsentType, PatientCodeStatusType
from care.utils.tests.test_utils import TestUtils


class TestPatientConsent(TestUtils, APITestCase):
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
        cls.consultation = cls.create_consultation(
            cls.patient1, cls.facility, cls.doctor
        )
        cls.patient2 = cls.create_patient(cls.district, cls.facility)
        cls.consultation2 = cls.create_consultation(
            cls.patient2, cls.facility, cls.doctor
        )

    def test_create_consent(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.CONSENT_FOR_ADMISSION,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["type"], ConsentType.CONSENT_FOR_ADMISSION)

    def test_list_consent(self):
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("results")), 0)

        self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.CONSENT_FOR_ADMISSION,
            },
        )
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("results")), 1)

    def test_retrieve_consent(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.CONSENT_FOR_ADMISSION,
            },
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/{response.data['id']}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["type"], ConsentType.CONSENT_FOR_ADMISSION)

    def test_update_consent(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.CONSENT_FOR_ADMISSION,
            },
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.patch(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/{response.data['id']}/",
            {
                "type": ConsentType.CONSENT_FOR_PROCEDURE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["type"], ConsentType.CONSENT_FOR_PROCEDURE)

    def test_auto_archive_consents(self):
        response_1 = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.PATIENT_CODE_STATUS,
                "patient_code_status": PatientCodeStatusType.ACTIVE_TREATMENT,
            },
        )
        self.assertEqual(response_1.status_code, 201)

        upload_response = self.client.post(
            "/api/v1/files/",
            {
                "original_name": "test.pdf",
                "file_type": "CONSENT_RECORD",
                "name": "Test File",
                "associating_id": response_1.data["id"],
                "file_category": "UNSPECIFIED",
                "mime_type": "application/pdf",
            },
        )

        self.assertEqual(upload_response.status_code, 201)

        response_2 = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.PATIENT_CODE_STATUS,
                "patient_code_status": PatientCodeStatusType.COMFORT_CARE,
            },
        )

        self.assertEqual(response_2.status_code, 201)

        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/{response_1.data['id']}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["archived"], True)

        files = self.client.get(
            f"/api/v1/files/?associating_id={response_1.data['id']}&file_type=CONSENT_RECORD&is_archived=false"
        )

        self.assertEqual(files.status_code, 200)
        self.assertEqual(files.data["count"], 0)

    def test_patient_code_status_constraint(self):
        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.PATIENT_CODE_STATUS,
            },
        )

        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            f"/api/v1/consultation/{self.consultation.external_id}/consents/",
            {
                "type": ConsentType.CONSENT_FOR_ADMISSION,
                "patient_code_status": PatientCodeStatusType.ACTIVE_TREATMENT,
            },
        )

        self.assertEqual(response.status_code, 400)
