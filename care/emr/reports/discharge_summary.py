import logging
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils import timezone

from care.emr.models import Encounter, FileUpload
from care.emr.reports import SectionRegistry
from care.emr.reports.renderer.renderer_registry import RendererRegistry
from care.emr.reports.utils import (
    TypstHeaderBuilder,
    download_image_to_cache,
)
from care.emr.resources.file_upload.spec import FileCategoryChoices, FileTypeChoices
from care.emr.resources.template.spec import FacilityReportTemplateType
from care.facility.models import FacilityReportTemplate

logger = logging.getLogger(__name__)

LOCK_DURATION = 2 * 60  # 2 minutes


def _cache_key(prefix, enc_id):
    return f"{prefix}_{enc_id}"


def set_lock(enc_id: str, progress: int):
    cache.set(_cache_key("discharge_summary", enc_id), progress, timeout=LOCK_DURATION)


def get_progress(enc_id: str) -> int | None:
    return cache.get(_cache_key("discharge_summary", enc_id))


def clear_lock(enc_id: str):
    cache.delete(_cache_key("discharge_summary", enc_id))


def extract_images(images: list, config: dict):
    """Extract image information from configuration sections"""
    for row in config["header"].get("rows", []):
        for el in row:
            if el["type"] == "image":
                images.append((el["file_name"], el["url"]))

    # TODO: Add support for images in sections


def get_discharge_summary_template(
    encounter: Encounter, config: dict, render_format: str
) -> tuple[str, list]:
    """Generate Typst template for discharge summary"""
    logger.info("Building Typst template for %s", encounter.external_id)

    included_images = []

    page_layout = render_to_string(
        "reports/typst/page_layout.typ",
        {"layout": config["layout"]},
    )

    if render_format == "typst":
        hb = TypstHeaderBuilder.from_config(config["header"])
        header_typst = hb.render()

    fragments = []
    ctx = {"encounter": encounter}

    renderer = RendererRegistry.get(render_format)

    for section_conf in config["sections"]:
        if not section_conf.get("enabled", False):
            continue

        cls = SectionRegistry.get(section_conf["source"])
        if not cls:
            logger.warning("No handler for source %r", section_conf["source"])
            continue

        section = cls(section_conf, ctx, renderer())
        fragments.append(section.render())

    extract_images(included_images, config)

    return "\n\n".join([page_layout, header_typst, *fragments]), included_images


def compile_typ(
    output_file: str, template_code: str, included_images: list, enc_id: str
):
    """Compile Typst template into PDF"""
    logger.info("Compiling PDF for %s → %s", enc_id, output_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "template.typ"
        template_path.write_text(template_code)

        for file_name, url in included_images:
            logo_bytes = download_image_to_cache(file_name, url)
            with Path.open(Path(tmpdir) / file_name, "wb") as f:
                f.write(logo_bytes)

        subprocess.run(  # noqa: S603
            [settings.TYPST_BIN, "compile", str(template_path.name), str(output_file)],
            cwd=tmpdir,
            check=False,
        )

    logger.info("Successfully compiled PDF for %s", enc_id)


def generate_and_upload_discharge_summary(
    encounter: Encounter, render_format: str = "typst"
) -> FileUpload | None:
    """Generate and upload discharge summary PDF for an encounter"""
    enc_id = encounter.external_id
    logger.info("Starting Discharge Summary for %s", enc_id)
    set_lock(enc_id, 5)

    try:
        config = FacilityReportTemplate.objects.get(
            facility=encounter.facility,
            type=FacilityReportTemplateType.discharge_summary,
        ).config

        now_ts = int(timezone.now().timestamp() * 1000)
        slug = encounter.patient.name.lower().replace(" ", "_")
        summary_file = FileUpload(
            name=f"discharge_summary-{slug}-{now_ts}",
            internal_name=f"{uuid4()}{now_ts}.pdf",
            file_type=FileTypeChoices.encounter.value,
            file_category=FileCategoryChoices.discharge_summary.value,
            associating_id=enc_id,
        )

        set_lock(enc_id, 10)
        template_code, included_images = get_discharge_summary_template(
            encounter, config, render_format
        )

        set_lock(enc_id, 50)

        # TODO: Need to update functions to call functions related to specific render_format
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_pdf:
            if render_format == "typst":
                logger.info("Compiling Typst for %s", enc_id)
                compile_typ(tmp_pdf.name, template_code, included_images, enc_id)
            logger.info("Uploading PDF for %s", enc_id)
            summary_file.files_manager.put_object(
                summary_file, tmp_pdf, ContentType="application/pdf"
            )

            summary_file.upload_completed = True
            summary_file.save(skip_internal_name=True)
            logger.info(
                "Uploaded Discharge Summary for %s (file id: %s)",
                enc_id,
                summary_file.id,
            )

    finally:
        clear_lock(enc_id)

    return summary_file


def generate_discharge_report_signed_url(
    patient_external_id: str, render_format: str
) -> str | None:
    """Generate a signed URL for the latest discharge report of a patient"""
    enc = (
        Encounter.objects.filter(patient__external_id=patient_external_id)
        .order_by("-created_date")
        .first()
    )

    if not enc:
        return None

    summary_file = generate_and_upload_discharge_summary(enc, render_format)
    return summary_file.files_manager.signed_url(
        summary_file,
        duration=2 * 24 * 60 * 60,  # 2 days
    )
