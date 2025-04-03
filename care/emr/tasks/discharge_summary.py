from logging import Logger

from botocore.exceptions import ClientError
from celery import shared_task
from celery.utils.log import get_task_logger

from care.emr.models.encounter import Encounter
from care.emr.reports.discharge_summary import generate_and_upload_discharge_summary
from care.utils.exceptions import CeleryTaskError

logger: Logger = get_task_logger(__name__)


@shared_task(
    autoretry_for=(ClientError,), retry_kwargs={"max_retries": 3}, expires=10 * 60
)
def generate_discharge_summary_task(encounter_ext_id: str):
    """
    Generate and Upload the Discharge Summary
    """
    logger.info("Generating Discharge Summary for %s", encounter_ext_id)
    try:
        encounter = Encounter.objects.get(external_id=encounter_ext_id)
    except Encounter.DoesNotExist as e:
        msg = f"Encounter {encounter_ext_id} does not exist"
        raise CeleryTaskError(msg) from e

    summary_file = generate_and_upload_discharge_summary(encounter)
    if not summary_file:
        msg = "Unable to generate discharge summary"
        raise CeleryTaskError(msg)

    return summary_file.id
