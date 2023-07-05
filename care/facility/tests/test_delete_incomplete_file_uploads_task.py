from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from care.facility.models.file_upload import FileUpload
from care.facility.tasks.cleanup import delete_incomplete_file_uploads


class DeleteIncompleteFileUploadsTest(TestCase):
    def test_delete_incomplete_file_uploads_with_mock_s3(self):
        yesterday = timezone.now() - timezone.timedelta(days=1)

        # Create dummy FileUpload objects
        with freeze_time(yesterday):
            file_upload1 = FileUpload.objects.create(
                file_type=FileUpload.FileType.PATIENT.value,
                internal_name="file1.pdf",
                upload_completed=False,
            )
            file_upload2 = FileUpload.objects.create(
                file_type=FileUpload.FileType.PATIENT.value,
                internal_name="file2.jpg",
                upload_completed=False,
            )
            file_upload3 = FileUpload.objects.create(
                file_type=FileUpload.FileType.PATIENT.value,
                internal_name="file3.csv",
                upload_completed=True,
            )

        # Patch the bulk_delete_objects method
        with patch(
            "care.facility.models.file_upload.FileUpload.bulk_delete_objects"
        ) as mock_bulk_delete_objects:
            # Call the Celery task
            delete_incomplete_file_uploads()

            # Assert
            self.assertFalse(FileUpload.objects.filter(pk=file_upload1.pk).exists())
            self.assertFalse(FileUpload.objects.filter(pk=file_upload2.pk).exists())
            self.assertTrue(FileUpload.objects.filter(pk=file_upload3.pk).exists())

            mock_bulk_delete_objects.assert_called_once_with(
                [
                    f"{file_upload1.FileType(file_upload1.file_type).name}/{file_upload1.internal_name}",
                    f"{file_upload2.FileType(file_upload2.file_type).name}/{file_upload2.internal_name}",
                ]
            )
