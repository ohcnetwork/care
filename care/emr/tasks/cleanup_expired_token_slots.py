from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from care.emr.models import TokenSlot

logger: Logger = get_task_logger(__name__)


@shared_task
def cleanup_expired_token_slots():
    """
    Hard-deletes TokenSlot objects that have expired if they have no bookings associated with them.
    """
    logger.info("Cleaning up expired TokenSlot objects")
    queryset = TokenSlot.objects.filter(
        tokenbooking__isnull=True, end_datetime__lte=timezone.now()
    )
    queryset.delete()
