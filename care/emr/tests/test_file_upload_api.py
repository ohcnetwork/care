import base64
import io
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from care.emr.models.file_upload import FileUpload
from care.emr.tasks.cleanup_incomplete_file_uploads import (
    cleanup_incomplete_file_uploads,
)
from care.utils.tests.base import CareAPITestBase


@override_settings(
    FILE_UPLOAD_BUCKET="patient-test", FACILITY_S3_BUCKET="facility-test"
)
class FileUploadTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        storage = patch("care.emr.utils.file_manager.boto3.client")
        self.addCleanup(storage.stop)
        self.s3 = storage.start().return_value
        self.s3.generate_presigned_url.side_effect = (
            lambda operation, **kwargs: f"https://storage.test/{operation}"
        )
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
        self.s3.put_object.assert_called_once()
        self.assertEqual(
            self.s3.put_object.call_args.kwargs["Key"], self.user.profile_picture_url
        )
        self.assertEqual(self.s3.put_object.call_args.kwargs["Bucket"], "facility-test")

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
        self.s3.put_object.assert_called_once()
        self.assertEqual(
            self.s3.put_object.call_args.kwargs["Key"], self.facility.cover_image_url
        )
        self.assertEqual(self.s3.put_object.call_args.kwargs["Bucket"], "facility-test")

    def test_upload_patient_file(self):
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
        self.assertFalse(file_obj.upload_completed)
        self.assertEqual(response.data["signed_url"], "https://storage.test/put_object")
        self.s3.generate_presigned_url.assert_called_once_with(
            "put_object",
            Params={
                "Bucket": "patient-test",
                "Key": f"patient/{file_obj.internal_name}",
                "ContentType": self.file_mime_type,
            },
            ExpiresIn=3600,
        )

        response = self.client.post(
            reverse("files-mark-upload-completed", args=[response.data["id"]]),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        file_obj.refresh_from_db()
        self.assertTrue(file_obj.upload_completed)
        self.assertEqual(file_obj.updated_by, self.user)

        response = self.client.get(
            reverse("files-detail", args=[response.data["id"]]),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["read_signed_url"], "https://storage.test/get_object"
        )
        self.s3.generate_presigned_url.assert_called_with(
            "get_object",
            Params={
                "Bucket": "patient-test",
                "Key": f"patient/{file_obj.internal_name}",
                "ResponseContentDisposition": "inline; filename=file.jpg",
            },
            ExpiresIn=3600,
        )

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

        file_obj = FileUpload.objects.get(external_id=response.data["id"])
        self.assertTrue(file_obj.upload_completed)
        self.assertEqual(file_obj.meta["mime_type"], self.file_mime_type)
        self.assertEqual(file_obj.created_by, self.user)
        self.assertEqual(file_obj.updated_by, self.user)
        self.s3.put_object.assert_called_once()
        upload_params = self.s3.put_object.call_args.kwargs
        self.assertEqual(upload_params["Bucket"], "patient-test")
        self.assertEqual(upload_params["Key"], f"patient/{file_obj.internal_name}")
        self.assertEqual(upload_params["Body"].read(), self.file.getvalue())
        self.assertEqual(
            response.data["read_signed_url"], "https://storage.test/get_object"
        )

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

        cleanup_incomplete_file_uploads()

        self.s3.delete_object.assert_called_once_with(
            Bucket="patient-test", Key=f"patient/{file_obj.internal_name}"
        )
        self.assertFalse(FileUpload.objects.filter(pk=file_obj.pk).exists())

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

    def test_cleanup_retains_completed_and_recent_uploads(self):
        completed = FileUpload.objects.create(
            name="Completed",
            internal_name="completed.jpg",
            file_type="patient",
            file_category="unspecified",
            associating_id=str(self.patient.external_id),
            upload_completed=True,
        )
        recent = FileUpload.objects.create(
            name="Recent",
            internal_name="recent.jpg",
            file_type="patient",
            file_category="unspecified",
            associating_id=str(self.patient.external_id),
        )
        FileUpload.objects.filter(pk=completed.pk).update(
            created_date=timezone.now()
            - timedelta(hours=settings.FILE_UPLOAD_EXPIRY_HOURS + 1)
        )

        cleanup_incomplete_file_uploads()

        self.assertCountEqual(
            FileUpload.objects.values_list("pk", flat=True),
            [completed.pk, recent.pk],
        )
        self.s3.delete_object.assert_not_called()

    def test_failed_direct_upload_rolls_back_database_record(self):
        self.s3.put_object.side_effect = RuntimeError("Storage unavailable")
        response = self.client.post(
            reverse("files-upload-file"),
            {
                "name": "file",
                "original_name": "file.jpg",
                "file_type": "patient",
                "file_category": "unspecified",
                "associating_id": str(self.patient.external_id),
                "file_data": base64.b64encode(self.file.getvalue()).decode(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("Failed to upload file to storage", str(response.data))
        self.s3.put_object.assert_called_once()
        self.assertFalse(FileUpload.objects.exists())

    def test_list_files_without_required_params(self):
        response = self.client.get(reverse("files-list"))
        self.assertEqual(response.status_code, 403)

    def test_list_files_with_params(self):
        url = reverse("files-list")
        created = self.client.post(
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
        self.assertEqual(created.status_code, 200, created.data)
        filters = {
            "file_type": "patient",
            "associating_id": str(self.patient.external_id),
        }
        response = self.client.get(url, filters)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

        completed = self.client.post(
            reverse("files-mark-upload-completed", args=[created.data["id"]])
        )
        self.assertEqual(completed.status_code, 200, completed.data)
        response = self.client.get(
            url,
            filters,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [created.data["id"]]
        )

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
