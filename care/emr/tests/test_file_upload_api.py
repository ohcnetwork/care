import io
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from care.emr.models.file_upload import FileUpload
from care.emr.tasks.cleanup_incomplete_file_uploads import (
    cleanup_incomplete_file_uploads,
)
from care.utils.tests.base import CareAPITestBase


def response_content(response) -> bytes:
    """Collect a streaming FileResponse body."""
    return b"".join(response.streaming_content)


class FileUploadTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()  # using su to skip authz checks
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()

        self.file = io.BytesIO()
        image = Image.new("RGB", (800, 800))
        image.save(self.file, format="JPEG")
        self.file.name = "file.jpg"
        self.file_mime_type = "image/jpeg"
        self.file.seek(0)

        self.client.force_authenticate(user=self.user)

    def upload_payload(self, **overrides):
        """A valid multipart upload body (ADR-0002)."""
        payload = {
            "file": SimpleUploadedFile(
                self.file.name, self.file.getvalue(), content_type=self.file_mime_type
            ),
            "name": "file",
            "file_type": "patient",
            "file_category": "unspecified",
            "associating_id": str(self.patient.external_id),
        }
        payload.update(overrides)
        return payload

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
        upload = self.client.post(
            reverse("files-upload-file"),
            self.upload_payload(),
            format="multipart",
        )
        self.assertEqual(upload.status_code, 200, upload.data)

        detail = self.client.get(reverse("files-detail", args=[upload.data["id"]]))
        self.assertEqual(detail.status_code, 200, detail.data)

        # The download URL is a CARE route, not a storage-provider URL.
        download_url = detail.data["download_url"]
        self.assertEqual(
            download_url, reverse("files-download", args=[upload.data["id"]])
        )

        file_response = self.client.get(download_url)
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(response_content(file_response), self.file.getvalue())
        self.assertEqual(file_response.headers["Content-Type"], self.file_mime_type)
        # An inline-safe type still renders inline, as the presigned
        # ResponseContentDisposition used to arrange.
        self.assertEqual(
            file_response.headers["Content-Disposition"],
            f'inline; filename="{self.file.name}"',
            file_response.headers,
        )

    def test_direct_file_upload(self):
        response = self.client.post(
            reverse("files-upload-file"),
            self.upload_payload(),
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)

        file_response = self.client.get(response.data["download_url"])
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(response_content(file_response), self.file.getvalue())

    def test_cleanup_incomplete_file_uploads(self):
        url = reverse("files-list")
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
        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        file_obj.created_date = file_obj.created_date - timedelta(
            hours=settings.FILE_UPLOAD_EXPIRY_HOURS + 1
        )
        file_obj.save()

        # Put a real object behind the incomplete row, through Django Storage.
        file_obj.files_manager.put_object(file_obj, ContentFile(self.file.getvalue()))
        self.assertTrue(file_obj.files_manager.exists(file_obj))

        cleanup_incomplete_file_uploads.delay()

        # Provider-neutral assertions: the object is gone, and opening it
        # raises the standard Django Storage error rather than a boto3 one.
        self.assertFalse(file_obj.files_manager.exists(file_obj))
        with self.assertRaises(FileNotFoundError):
            file_obj.files_manager.get_object(file_obj)

        with self.assertRaises(FileUpload.DoesNotExist):
            file_obj.refresh_from_db()

    def test_archive_file(self):
        url = reverse("files-list")
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
        file_id = response.data["id"]

        self.client.post(
            reverse("files-mark-upload-completed", args=[file_id]), format="json"
        )

        archive_url = reverse("files-archive", args=[file_id])
        response = self.client.post(
            archive_url, {"archive_reason": "No longer needed"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_archived"])
        self.assertEqual(response.data["archive_reason"], "No longer needed")

    def test_list_files_without_required_params(self):
        response = self.client.get(reverse("files-list"))
        self.assertEqual(response.status_code, 403)

    def test_list_files_with_params(self):
        url = reverse("files-list")
        self.client.post(
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
        response = self.client.get(
            url,
            {
                "file_type": "patient",
                "associating_id": str(self.patient.external_id),
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_create_file_with_invalid_mime_type(self):
        url = reverse("files-list")
        response = self.client.post(
            url,
            {
                "name": "file",
                "original_name": "file.exe",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "mime_type": "application/x-msdownload",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_file_with_empty_original_name(self):
        url = reverse("files-list")
        response = self.client.post(
            url,
            {
                "name": "file",
                "original_name": "",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "mime_type": self.file_mime_type,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_direct_upload_missing_fields(self):
        url = reverse("files-upload-file")
        response = self.client.post(
            url,
            {
                "name": "file",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "mime_type": self.file_mime_type,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_file_name(self):
        url = reverse("files-list")
        response = self.client.post(
            url,
            {
                "name": "original_name",
                "original_name": "file.jpg",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "mime_type": self.file_mime_type,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        file_id = response.data["id"]
        detail_url = reverse("files-detail", args=[file_id])
        response = self.client.put(detail_url, {"name": "updated_name"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "updated_name")
