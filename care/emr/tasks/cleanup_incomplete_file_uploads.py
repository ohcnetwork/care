from datetime import timedelta
from logging import Logger

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
        ids_to_delete = []
        for file in queryset:
            if file.internal_name:
                try:
                    file_manager.delete_object(file, quiet=True)
                except Exception as e:
                    logger.error(
                        "Failed to delete file upload object %s: %s",
                        file.id,
                        e,
                    )
                    raise e
                ids_to_delete.append(file.id)

        deleted_count = FileUpload.objects.filter(id__in=ids_to_delete).delete()

        logger.info("Deleted %d incomplete file uploads", deleted_count)

        # re-fetch the queryset
        queryset = FileUpload.objects.filter(
            upload_completed=False,
            created_date__lte=threshold,
        )[:page_size]

    logger.info("Completed cleanup of incomplete file uploads")
    return True
