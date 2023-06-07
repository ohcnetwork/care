from datetime import timedelta

from celery.decorators import periodic_task
from celery.schedules import crontab
from django.utils import timezone

from care.facility.models.file_upload import FileUpload


@periodic_task(
    run_every=crontab(minute="0", hour="0")
)  # Run the task daily at midnight
def delete_incomplete_file_uploads():
    yesterday = timezone.now() - timedelta(days=1)
    incomplete_uploads = FileUpload.objects.filter(
        created__date__lte=yesterday, upload_completed=False
    )

    s3_keys = [
        f"{upload.FileType(upload.file_type).name/upload.internal_name}"
        for upload in incomplete_uploads
    ]

    FileUpload.bulk_delete_objects(s3_keys)
    incomplete_uploads.update(deleted=True)
