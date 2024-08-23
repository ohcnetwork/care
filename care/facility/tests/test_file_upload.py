from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models.file_upload import FileUpload
from care.utils.tests.test_utils import TestUtils


class FileUploadApiTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("nurse", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.consultation = cls.create_consultation(cls.patient, cls.facility)

    def test_file_upload_whitelist(self):
        for mime_type in ["application/pdf", "image/png", "image/jpeg"]:
            response = self.client.post(
                "/api/v1/files/",
                {
                    "original_name": f"test.{mime_type.split('/')[-1]}",
                    "file_type": "CONSULTATION",
                    "name": "Test File",
                    "associating_id": self.consultation.external_id,
                    "file_category": "UNSPECIFIED",
                    "mime_type": mime_type,
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for mime_type in ["image/gif"]:
            response = self.client.post(
                "/api/v1/files/",
                {
                    "original_name": f"test.{mime_type.split('/')[-1]}",
                    "file_type": "CONSULTATION",
                    "name": "Test File",
                    "associating_id": self.consultation.external_id,
                    "file_category": "UNSPECIFIED",
                    mime_type: mime_type,
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ConsentFileUploadApiTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("nurse", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.consultation = cls.create_consultation(cls.patient, cls.facility)
        cls.consent = cls.create_patient_consent(cls.consultation, created_by=cls.user)

    def test_consent_file_upload(self):
        upload_response = self.client.post(
            "/api/v1/files/",
            {
                "original_name": "test.pdf",
                "file_type": "CONSENT_RECORD",
                "name": "Test File",
                "associating_id": self.consent.external_id,
                "file_category": "UNSPECIFIED",
                "mime_type": "application/pdf",
            },
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            FileUpload.objects.filter(associating_id=self.consent.external_id).count(),
            1,
        )

        all_files = self.client.get(
            f"/api/v1/files/?associating_id={self.consent.external_id}&file_type=CONSENT_RECORD&is_archived=false"
        )

        self.assertEqual(all_files.status_code, status.HTTP_200_OK)
        self.assertEqual(all_files.data["count"], 1)
        self.assertEqual(all_files.data["results"][0]["name"], "Test File")
