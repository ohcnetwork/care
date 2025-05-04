import logging
import tempfile
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

from care.emr.models import Encounter, FileUpload
from care.emr.models.template import FacilityReportTemplate
from care.emr.registries.report.renderer import RendererRegistry
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.renderer.base import Renderer
from care.emr.resources.file_upload.spec import FileCategoryChoices, FileTypeChoices
from care.emr.resources.template.spec import FacilityReportTemplateType

logger = logging.getLogger(__name__)

LOCK_DURATION = 2 * 60  # 2 minutes


def _cache_key(prefix, encounter_external_id):
    return f"{prefix}_{encounter_external_id}"


def set_lock(encounter_external_id: str, progress: int):
    cache.set(
        _cache_key("discharge_summary", encounter_external_id),
        progress,
        timeout=LOCK_DURATION,
    )


def get_progress(encounter_external_id: str) -> int | None:
    return cache.get(_cache_key("discharge_summary", encounter_external_id))


def clear_lock(encounter_external_id: str):
    cache.delete(_cache_key("discharge_summary", encounter_external_id))


def extract_images(images: list, config: dict):
    """Extract image information from configuration sections"""
    for row in config["header"].get("rows", []):
        for el in row:
            if el["type"] == "image":
                images.append((el["file_name"], el["url"]))

    # TODO: Add support for images in sections


def get_discharge_summary_template(
    encounter: Encounter, config: dict, renderer: Renderer
) -> tuple[str, list]:
    logger.info(
        "Building discharge summary for %s in format %s",
        encounter.external_id,
        renderer.name,
    )

    included_images = []
    ctx = {"encounter": encounter}

    page_layout = renderer.render_page_layout(config["layout"])

    header_content = renderer.render_header(config["header"])

    fragments = []
    for section_conf in config["sections"]:
        if not section_conf.get("enabled", False):
            continue

        section_cls = SectionRegistry.get(section_conf["source"])
        if not section_cls:
            logger.warning("No handler for source %r", section_conf["source"])
            continue

        section = section_cls(section_conf, ctx, renderer)
        fragments.append(section.render())

    extract_images(included_images, config)

    final_content = "\n\n".join([page_layout, header_content, *fragments])
    return final_content, included_images


def generate_and_upload_discharge_summary(
    encounter: Encounter, render_format: str
) -> FileUpload | None:
    """Generate and upload discharge summary PDF for an encounter"""
    encounter_external_id = encounter.external_id
    logger.info("Starting Discharge Summary for %s", encounter_external_id)
    set_lock(str(encounter_external_id), 5)

    renderer_cls = RendererRegistry.get(render_format)
    if not renderer_cls:
        logger.warning("No handler for format %r", render_format)
        return None
    renderer = renderer_cls()
    try:
        config = (
            FacilityReportTemplate.objects.filter(
                facility=encounter.facility,
                type=FacilityReportTemplateType.discharge_summary,
            )
            .first()
            .config
        )

        now_ts = int(timezone.now().timestamp() * 1000)
        slug = encounter.patient.name.lower().replace(" ", "_")
        summary_file = FileUpload(
            name=f"discharge_summary-{slug}-{now_ts}",
            internal_name=f"{uuid4()}{now_ts}.pdf",
            file_type=FileTypeChoices.encounter.value,
            file_category=FileCategoryChoices.discharge_summary.value,
            associating_id=encounter_external_id,
        )

        set_lock(str(encounter_external_id), 10)
        template_code, included_images = get_discharge_summary_template(
            encounter, config, renderer
        )

        set_lock(str(encounter_external_id), 50)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_pdf:
            try:
                renderer.compile(
                    tmp_pdf.name,
                    template_code,
                    included_images,
                    str(encounter_external_id),
                )
            except Exception as e:
                logger.error(
                    "Error generating PDF for %s: %s", encounter_external_id, e
                )
                return None
            logger.info("Uploading PDF for %s", encounter_external_id)
            summary_file.files_manager.put_object(
                summary_file, tmp_pdf, ContentType="application/pdf"
            )

            summary_file.upload_completed = True
            summary_file.save(skip_internal_name=True)
            logger.info(
                "Uploaded Discharge Summary for %s (file id: %s)",
                encounter_external_id,
                summary_file.id,
            )

    finally:
        clear_lock(str(encounter_external_id))

    return summary_file


def generate_discharge_report_signed_url(
    patient_external_id: str, render_format: str
) -> str | None:
    """Generate a signed URL for the latest discharge report of a patient"""
    encounter = (
        Encounter.objects.filter(patient__external_id=patient_external_id)
        .order_by("-created_date")
        .first()
    )

    if not encounter:
        return None

    summary_file = generate_and_upload_discharge_summary(encounter, render_format)
    return summary_file.files_manager.signed_url(
        summary_file,
        duration=2 * 24 * 60 * 60,  # 2 days
    )
