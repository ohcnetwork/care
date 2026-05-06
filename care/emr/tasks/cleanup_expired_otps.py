from datetime import timedelta
from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger

from care.facility.models.patient import PatientMobileOTP
from care.utils.time_util import care_now

logger: Logger = get_task_logger(__name__)


@shared_task
def cleanup_expired_otps():
    """
    Soft-deletes PatientMobileOTP rows older than 24 hours
    """
    cutoff = care_now() - timedelta(hours=24)
    count = PatientMobileOTP.objects.filter(created_date__lt=cutoff).update(
        deleted=True
    )
    logger.info("Soft-deleted %d expired OTP rows", count)
