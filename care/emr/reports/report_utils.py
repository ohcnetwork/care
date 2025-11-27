import logging
import time
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

from care.emr.models.report.report_upload import ReportUpload
from care.emr.models.report.template import Template
from care.emr.reports.context_builder.report_builder import ReportContextBuilder
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.renderer.renderer import Renderer
from care.emr.reports.renderer.template_engine import TemplateEngine

logger = logging.getLogger(__name__)

LOCK_DURATION = 2 * 60


def set_lock(key: str, progress: int, timeout: int = LOCK_DURATION) -> None:
    cache_key = f"report_generation_lock:{key}"
    cache.set(cache_key, progress, timeout)


def get_progress(key: str) -> int | None:
    cache_key = f"report_generation_lock:{key}"
    return cache.get(cache_key)


def clear_lock(key: str) -> None:
    cache_key = f"report_generation_lock:{key}"
    cache.delete(cache_key)


def generate_and_upload_report(  # noqa: PLR0915
    template: Template,
    report_type: str,
    associating_id: str,
    context_config: dict,
    output_format: str = "pdf",
    options: dict | None = None,
    **kwargs,
) -> ReportUpload:
    logger.info(
        "Starting report generation and upload - report_type: %s, associating_id: %s, output_format: %s",
        report_type,
        associating_id,
        output_format,
    )

    options = options or {}
    context_builder = ReportContextBuilder()

    ctx = {}
    ctx.update(**kwargs)

    logger.debug("Building context with config keys: %s", list(context_config.keys()))
    context = context_builder.build_context(
        ctx=ctx,
        config=context_config,
    )
    logger.info("Context built successfully with %s top-level keys", len(context))

    template_engine = TemplateEngine()

    format_lower = output_format.lower()
    try:
        generator_class = GeneratorRegistry.get(format_lower)
        generator = generator_class()
        format_config = GeneratorRegistry.get_format_config(format_lower)
        file_extension = format_config["file_extension"]
        mime_type = format_config["mime_type"]
    except KeyError as e:
        error_msg = f"Unsupported output format: {output_format}. {e!s}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e

    logger.debug(
        "Using output format: %s, generator: %s, mime: %s, ext: %s",
        output_format,
        generator.__class__.__name__,
        mime_type,
        file_extension,
    )

    renderer = Renderer(template_engine, generator)

    logger.debug("Validating template syntax")
    valid, error = renderer.validate_syntax(template.template_data)
    if not valid:
        error_msg = f"Template validation failed: {error}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    logger.debug("Template syntax validation successful")

    logger.info("Rendering template with context")
    output_bytes = renderer.render(template.template_data, context, options)
    logger.info(
        "Template rendered successfully, output size: %s bytes", len(output_bytes)
    )

    current_date = timezone.now()
    timestamp = int(current_date.timestamp() * 1000)

    report_name = f"{report_type}-{associating_id}-{timestamp}"
    internal_name = f"{uuid4()}{int(time.time())}{file_extension}"

    logger.debug(
        "Creating ReportUpload record - name: %s, internal_name: %s",
        report_name,
        internal_name,
    )

    user_id = kwargs.get("user_id")

    report_upload = ReportUpload(
        template=template,
        name=report_name,
        internal_name=internal_name,
        associating_id=associating_id,
        report_type=report_type,
        upload_completed=False,
    )

    if user_id:
        from care.users.models import User

        try:
            report_upload.created_by = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(
                "User with id %s not found, report will have no created_by", user_id
            )

    report_upload.meta["mime_type"] = mime_type
    report_upload.meta["generated_at"] = current_date.isoformat()
    report_upload.meta["template_id"] = str(template.external_id)
    report_upload.meta["output_format"] = output_format

    report_upload.save(skip_internal_name=True)
    logger.info(
        "ReportUpload record created with external_id: %s", report_upload.external_id
    )

    try:
        logger.info(
            "Uploading report to S3 - size: %s bytes, mime_type: %s",
            len(output_bytes),
            mime_type,
        )
        report_upload.files_manager.put_object(
            report_upload, output_bytes, ContentType=mime_type
        )
        report_upload.upload_completed = True
        report_upload.save()
        logger.info(
            "Report uploaded successfully to S3 - external_id: %s",
            report_upload.external_id,
        )
    except Exception as e:
        logger.exception(
            "Failed to upload report to S3 - external_id: %s, error: %s",
            report_upload.external_id,
            e,
        )
        logger.info(
            "Deleting failed ReportUpload record: %s", report_upload.external_id
        )
        report_upload.delete()
        raise

    logger.info(
        "Report generation and upload completed successfully - external_id: %s, name: %s",
        report_upload.external_id,
        report_upload.name,
    )
    return report_upload
