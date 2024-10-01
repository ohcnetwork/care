from collections.abc import Iterable
from logging import Logger
from smtplib import SMTPException

from botocore.exceptions import ClientError
from celery import shared_task
from celery.utils.log import get_task_logger

from care.facility.models import PatientConsultation
from care.facility.models.file_upload import FileUpload
from care.facility.utils.reports.discharge_summary import (
    email_discharge_summary,
    generate_and_upload_discharge_summary,
)
from care.utils.exceptions import CeleryTaskError

logger: Logger = get_task_logger(__name__)


@shared_task(
    autoretry_for=(ClientError,), retry_kwargs={"max_retries": 3}, expires=10 * 60
)
def generate_discharge_summary_task(consultation_ext_id: str):
    """
    Generate and Upload the Discharge Summary
    """
    logger.info("Generating Discharge Summary for %s", consultation_ext_id)
    try:
        consultation = PatientConsultation.objects.get(external_id=consultation_ext_id)
    except PatientConsultation.DoesNotExist as e:
        msg = f"Consultation {consultation_ext_id} does not exist"
        raise CeleryTaskError(msg) from e

    summary_file = generate_and_upload_discharge_summary(consultation)
    if not summary_file:
        msg = "Unable to generate discharge summary"
        raise CeleryTaskError(msg)

    return summary_file.id


@shared_task(
    autoretry_for=(ClientError, SMTPException),
    retry_kwargs={"max_retries": 3},
    expires=10 * 60,
)
def email_discharge_summary_task(file_id: int, emails: Iterable[str]):
    logger.info("Emailing Discharge Summary %s to %s", file_id, emails)
    try:
        summary = FileUpload.objects.get(id=file_id)
    except FileUpload.DoesNotExist:
        logger.error("Summary %s does not exist", file_id)
        return False
    email_discharge_summary(summary, emails)
    return True
