from datetime import timedelta
from logging import Logger

from botocore.exceptions import ClientError
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone

from care.emr.models import FileUpload

logger: Logger = get_task_logger(__name__)


@shared_task()
def cleanup_incomplete_file_uploads():
    """
    Hard-deletes FileUpload objects that have not been completed.
    """
    threshold = timezone.now() - timedelta(hours=settings.FILE_UPLOAD_EXPIRY_HOURS)
    logger.info("Cleaning up incomplete file uploads")
    page_size = 1000
    queryset = FileUpload.objects.filter(
        upload_completed=False,
        created_date__lte=threshold,
    )[:page_size]

    file_manager = FileUpload.files_manager
    while queryset.exists():
        file_ids = queryset.values_list("id", flat=True)

        try:
            # delete the file from S3
            file_manager.delete_objects(queryset, quiet=True)
            FileUpload.objects.filter(id__in=file_ids).delete()
        except ClientError as e:
            logger.error(
                "Failed to delete file upload objects %s: %s",
                file_ids,
                e,
            )
            raise

        # re-fetch the queryset
        queryset = FileUpload.objects.filter(
            upload_completed=False,
            created_date__lte=threshold,
        )[:page_size]
