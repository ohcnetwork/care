from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from care.facility.models.file_upload import FileUpload
from care.facility.models.notification import Notification


@shared_task
def delete_old_notifications():
    ninety_days_ago = timezone.now() - timedelta(days=90)
    Notification.objects.filter(created_date__lte=ninety_days_ago).delete()


@shared_task
def delete_incomplete_file_uploads():
    yesterday = timezone.now() - timedelta(days=1)
    incomplete_uploads = FileUpload.objects.filter(
        created_date__lte=yesterday, upload_completed=False
    )

    s3_keys = [
        f"{upload.FileType(upload.file_type).name}/{upload.internal_name}"
        for upload in incomplete_uploads
    ]

    FileUpload.bulk_delete_objects(s3_keys)
    incomplete_uploads.update(deleted=True)
