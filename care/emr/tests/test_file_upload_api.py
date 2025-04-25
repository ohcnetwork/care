import base64
import io

import requests
from django.urls import reverse
from PIL import Image

from care.emr.models import SchedulableUserResource
from care.utils.tests.base import CareAPITestBase


class FileUploadTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()  # using su to skip authz checks
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.resource = SchedulableUserResource.objects.create(
            user=self.user,
            facility=self.facility,
        )
        self.patient = self.create_patient()

        self.file = io.BytesIO()
        image = Image.new("RGB", (800, 800))
        image.save(self.file, format="JPEG")
        self.file.name = "file.jpg"
        self.file_mime_type = "image/jpeg"
        self.file.seek(0)

        self.client.force_authenticate(user=self.user)

    def test_upload_user_avatar(self):
        url = reverse("users-profile-picture", args=[self.user.username])
        response = self.client.post(
            url,
            {"profile_picture": self.file},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_picture_url)

    def test_upload_facility_cover_image(self):
        url = reverse("facility-cover-image", args=[self.facility.external_id])
        response = self.client.post(
            url,
            {"cover_image": self.file},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.facility.refresh_from_db()
        self.assertTrue(self.facility.cover_image_url)

    def test_upload_patient_file(self):
        url = reverse("files-list")

        # create file object
        response = self.client.post(
            url,
            {
                "name": "file",
                "original_name": "file.jpg",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "mime_type": self.file_mime_type,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        # upload file to bucket
        file_upload_response = requests.put(
            response.data["signed_url"],
            data=self.file,
            headers={
                "Content-Type": self.file_mime_type,
                "x-ms-blob-type": "BlockBlob",
            },
            timeout=5,
        )
        self.assertIn(
            file_upload_response.status_code, [200, 201], file_upload_response.text
        )

        # mark upload as completed
        response = self.client.post(
            reverse("files-mark-upload-completed", args=[response.data["id"]]),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        # retrieve file object
        response = self.client.get(
            reverse("files-detail", args=[response.data["id"]]),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        # try to download the file from bucket
        file_response = requests.get(
            response.data["read_signed_url"],
            timeout=5,
        )
        self.assertEqual(file_response.status_code, 200, file_response.text)
        # verify the file contents
        self.assertEqual(file_response.content, self.file.getvalue())
        # verify the file headers
        self.assertEqual(
            file_response.headers["Content-Type"],
            self.file_mime_type,
            file_response.headers,
        )
        # azure does not support content-disposition
        # self.assertEqual(
        #     file_response.headers["Content-Disposition"],
        #     f"attachment; filename={self.file.name}",
        #     file_response.headers,
        # )

    def test_direct_file_upload(self):
        url = reverse("files-upload-file")
        response = self.client.post(
            url,
            {
                "name": "file",
                "original_name": "file.jpg",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "mime_type": self.file_mime_type,
                "file_data": base64.b64encode(self.file.read()).decode("utf-8"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)

        # verify the file contents
        file_response = requests.get(
            response.data["read_signed_url"],
            timeout=5,
        )
        self.assertEqual(file_response.status_code, 200, file_response.text)
        self.assertEqual(file_response.content, self.file.getvalue())
