import logging
import time
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

from care.emr.models.report.report_upload import ReportUpload
from care.emr.models.report.template import Template
from care.emr.reports.context_builder import SingleUserIdContextBuilder
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.renderer.renderer import Renderer
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.emr.reports.report_type_registry import ReportTypeRegistry
from care.emr.reports.report_type_utils import validate_associating_id
from care.users.models import User

logger = logging.getLogger(__name__)
LOCK_DURATION = 2 * 60


def get_lock_key(report_type: str, associating_id: str) -> str:
    return f"{report_type}_{associating_id}"


def set_lock(key: str, progress: int, timeout: int = LOCK_DURATION) -> None:
    cache_key = f"report_generation_lock:{key}"
    cache.set(cache_key, progress, timeout)


def get_progress(key: str) -> int | None:
    cache_key = f"report_generation_lock:{key}"
    return cache.get(cache_key)


def clear_lock(key: str) -> None:
    cache_key = f"report_generation_lock:{key}"
    cache.delete(cache_key)


def generate_and_upload_report(  # noqa:PLR0915
    template: Template,
    report_type: str,
    associating_id: str,
    output_format: str = "pdf",
    **kwargs,
) -> ReportUpload:
    context_class = DataPointRegistry.get(template.context)
    if not context_class:
        error_msg = f"Context '{template.context}' not found in DataPointRegistry"
        raise ValueError(error_msg)

    try:
        report_type_config = ReportTypeRegistry.get(report_type)
    except KeyError as e:
        error_msg = f"Report Type '{report_type}' not found in ReportTypeRegistry"
        raise ValueError(error_msg) from e

    associating_object = validate_associating_id(
        associating_model=report_type_config.associating_model,
        associating_id=associating_id,
        report_type_key=report_type,
    )

    context_key = context_class.context_key or template.context
    context = {context_key: context_class(context=associating_object)}

    user_id = kwargs.get("user_id")
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(
                "User with id %s not found, report will have no current_user", user_id
            )

    if user:
        context["current_user"] = SingleUserIdContextBuilder(context=user)
    else:
        context["current_user"] = SingleUserIdContextBuilder(is_preview=True)

    template_engine = TemplateEngine()
    format_lower = output_format.lower()

    generator_class = GeneratorRegistry.get(format_lower)
    generator = generator_class()
    format_config = GeneratorRegistry.get_format_config(format_lower)
    file_extension = format_config["file_extension"]
    mime_type = format_config["mime_type"]

    renderer = Renderer(generator, template_engine)

    validated_options = generator.options_model.model_validate(template.options)
    output_bytes = renderer.render(template.template_data, context, validated_options)

    current_date = timezone.now()
    timestamp = int(current_date.timestamp() * 1000)

    report_name = f"{template.name}-{associating_id}-{timestamp}"
    internal_name = f"{uuid4()}{int(time.time())}{file_extension}"

    report_upload = ReportUpload(
        template=template,
        name=report_name,
        internal_name=internal_name,
        associating_id=associating_id,
        report_type=report_type,
        upload_completed=False,
    )

    if user:
        report_upload.created_by = user

    report_upload.meta["mime_type"] = mime_type
    report_upload.meta["generated_at"] = current_date.isoformat()
    report_upload.meta["template_id"] = str(template.external_id)
    report_upload.meta["output_format"] = output_format

    report_upload.save(skip_internal_name=True)

    try:
        report_upload.files_manager.put_object(
            report_upload, output_bytes, ContentType=mime_type
        )
        report_upload.upload_completed = True
        report_upload.save()
    except Exception as e:
        report_upload.delete()
        raise e

    return report_upload
