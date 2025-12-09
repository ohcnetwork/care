from botocore.exceptions import ClientError
from celery import shared_task
from celery.utils.log import get_task_logger

from care.emr.models.report.template import Template
from care.emr.reports import report_utils
from care.utils.exceptions import CeleryTaskError

logger = get_task_logger(__name__)


@shared_task(
    autoretry_for=(ClientError,), retry_kwargs={"max_retries": 3}, expires=10 * 60
)
def generate_report_task(
    template_id: str,
    report_type: str,
    associating_id: str,
    output_format: str = "pdf",
    **kwargs,
):
    lock_key = f"{report_type}_{associating_id}"

    logger.info(
        "Starting report generation task - report_type: %s, "
        "associating_id: %s, template_id: %s, output_format: %s",
        report_type,
        associating_id,
        template_id,
        output_format,
    )

    try:
        logger.debug("Setting initial lock for %s at 10%% progress", lock_key)
        report_utils.set_lock(lock_key, 10)

        try:
            logger.debug("Fetching template with external_id: %s", template_id)
            template = Template.objects.get(external_id=template_id)
        except Template.DoesNotExist as e:
            logger.error("Template not found: %s", template_id)
            msg = f"Template {template_id} does not exist"
            raise CeleryTaskError(msg) from e

        logger.debug("Updating lock for %s to 30%% progress", lock_key)
        report_utils.set_lock(lock_key, 30)

        report_upload = report_utils.generate_and_upload_report(
            template=template,
            output_format=output_format,
            report_type=report_type,
            associating_id=associating_id,
            **kwargs,
        )

        if not report_upload:
            logger.error(
                "Report generation failed - generate_and_upload_report returned None"
            )
            raise CeleryTaskError("Unable to generate report")

        logger.info(
            "Report generation task completed - external_id: %s",
            report_upload.external_id,
        )
        return str(report_upload.external_id)

    except CeleryTaskError:
        logger.exception("Celery task error in report generation for %s", lock_key)
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error in report generation task for %s: %s", lock_key, e
        )
        raise e
    finally:
        logger.debug("Clearing lock for %s", lock_key)
        report_utils.clear_lock(lock_key)
