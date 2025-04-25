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
from care.emr.reports.utils import HeaderBuilder
from care.emr.resources.file_upload.spec import FileCategoryChoices, FileTypeChoices
from care.emr.resources.template.spec import FacilityReportTemplateType
from care.facility.models import FacilityReportTemplate

logger = logging.getLogger(__name__)

LOCK_DURATION = 2 * 60  # 2 minutes

LOGOS_DIR = Path(settings.BASE_DIR) / "care" / "templates" / "reports" / "logos"


def lock_key(enc_id: str) -> str:
    return f"discharge_summary_{enc_id}"


def set_lock(enc_id: str, progress: int):
    cache.set(lock_key(enc_id), progress, timeout=LOCK_DURATION)


def get_progress(enc_id: str) -> int | None:
    return cache.get(lock_key(enc_id))


def clear_lock(enc_id: str):
    cache.delete(lock_key(enc_id))


def get_discharge_summary_template(encounter: Encounter, config: dict) -> str:
    logger.info("Building Typst template for %s", encounter.external_id)

    page_layout = render_to_string(
        "reports/typst/page_layout.typ",
        {
            "layout": config["layout"],
        },
    )
    hb = HeaderBuilder.from_config(config["header"])
    header_typst = hb.render()

    fragments = []
    ctx = {"encounter": encounter}
    for section_conf in config["sections"]:
        if not section_conf.get("enabled", False):
            continue
        cls = SectionRegistry.get(section_conf["source"])
        if not cls:
            logger.warning("No handler for source %r", section_conf["source"])
            continue
        section = cls(section_conf, ctx)
        frag = section.render()
        fragments.append(frag)

    return "\n\n".join([page_layout, header_typst, *fragments])


def compile_typ(output_file: str, template_code: str, config: dict, enc_id: str):
    logger.info("Compiling PDF for %s → %s", enc_id, output_file)

    logo_name = config["header"]["logo"]["file_name"]
    logo_path = LOGOS_DIR / logo_name

    with tempfile.TemporaryDirectory() as tmpdir:
        template = Path(tmpdir) / "template.typ"
        template.write_text(template_code)
        logo_dest = Path(tmpdir) / f"{logo_name}"
        logo_dest.write_text(logo_path.read_text())

        subprocess.run(  # noqa: S603
            [
                settings.TYPST_BIN,
                "compile",
                str(template.name),
                str(output_file),
            ],
            cwd=tmpdir,
            check=False,
        )

    logger.info("Successfully compiled PDF for %s", enc_id)


def generate_discharge_summary_pdf(
    template_code: str, out_file, config: dict, encounter: Encounter
):
    logger.info("Generating Discharge Summary PDF for %s", encounter.external_id)
    compile_typ(out_file.name, template_code, config, encounter.external_id)
    logger.info("Generated Discharge Summary PDF for %s", encounter.external_id)


def generate_and_upload_discharge_summary(encounter: Encounter) -> FileUpload:
    logger.info("Starting Discharge Summary for %s", encounter.external_id)
    set_lock(encounter.external_id, 5)

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
            associating_id=encounter.external_id,
        )

        set_lock(encounter.external_id, 10)
        template_code = get_discharge_summary_template(encounter, config)

        set_lock(encounter.external_id, 50)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_pdf:
            generate_discharge_summary_pdf(template_code, tmp_pdf, config, encounter)
            logger.info("Uploading PDF for %s", encounter.external_id)
            summary_file.files_manager.put_object(
                summary_file, tmp_pdf, ContentType="application/pdf"
            )

            summary_file.upload_completed = True
            summary_file.save(skip_internal_name=True)
            logger.info(
                "Uploaded Discharge Summary for %s (file id: %s)",
                encounter.external_id,
                summary_file.id,
            )

    finally:
        clear_lock(encounter.external_id)

    return summary_file


def generate_discharge_report_signed_url(patient_external_id: str) -> str | None:
    enc = (
        Encounter.objects.filter(patient__external_id=patient_external_id)
        .order_by("-created_date")
        .first()
    )
    if not enc:
        return None
    summary_file = generate_and_upload_discharge_summary(enc)
    return summary_file.files_manager.signed_url(
        summary_file, duration=2 * 24 * 60 * 60
    )
