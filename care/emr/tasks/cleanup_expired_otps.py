from datetime import timedelta
from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from care.facility.models.patient import MobileOTP
from care.utils.time_util import care_now

logger: Logger = get_task_logger(__name__)


@shared_task
def cleanup_expired_otps():
    """
    Soft-deletes MobileOTP rows older than the lockout window
    """
    cutoff = care_now() - timedelta(minutes=settings.OTP_LOCKOUT_MINUTES)
    count = MobileOTP.objects.filter(created_date__lt=cutoff).update(deleted=True)
    logger.info("Soft-deleted %d expired OTP rows", count)
