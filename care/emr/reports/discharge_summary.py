import logging
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils import timezone

from care.emr.models import (
    AllergyIntolerance,
    Condition,
    Encounter,
    FileUpload,
    Observation,
    medication_request,
)
from care.emr.resources.allergy_intolerance.spec import (
    VerificationStatusChoices as AllergyVerificationStatusChoices,
)
from care.emr.resources.condition.spec import CategoryChoices, VerificationStatusChoices
from care.emr.resources.file_upload.spec import FileCategoryChoices, FileTypeChoices
from care.emr.resources.medication.request.spec import MedicationRequestStatus
from care.users.models import User

logger = logging.getLogger(__name__)

LOCK_DURATION = 2 * 60  # 2 minutes


def lock_key(encounter_ext_id: str):
    return f"discharge_summary_{encounter_ext_id}"


def set_lock(encounter_ext_id: str, progress: int):
    cache.set(lock_key(encounter_ext_id), progress, timeout=LOCK_DURATION)


def get_progress(encounter_ext_id: str):
    return cache.get(lock_key(encounter_ext_id))


def clear_lock(encounter_ext_id: str):
    cache.delete(lock_key(encounter_ext_id))


def parse_iso_datetime(date_str):
    try:
        return timezone.datetime.fromisoformat(date_str)
    except ValueError:
        return None


def format_duration(duration):
    if not duration:
        return ""

    if duration.days > 0:
        return f"{duration.days} days"
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}"


def get_discharge_summary_data(encounter: Encounter):
    logger.info("fetching discharge summary data for %s", encounter.external_id)
    symptoms = Condition.objects.filter(
        encounter=encounter,
        category=CategoryChoices.problem_list_item.value,
    ).exclude(verification_status=VerificationStatusChoices.entered_in_error)
    diagnoses = (
        Condition.objects.filter(
            encounter=encounter,
            category=CategoryChoices.encounter_diagnosis.value,
        )
        .exclude(verification_status=VerificationStatusChoices.entered_in_error)
        .order_by("id")
    )
    principal_diagnosis = diagnoses[0] if diagnoses else None

    allergies = sorted(
        AllergyIntolerance.objects.filter(encounter=encounter).exclude(
            verification_status=AllergyVerificationStatusChoices.entered_in_error
        ),
        key=lambda x: ("high", "low", "unable-to-assess", "", None).index(
            x.criticality
        ),
    )

    observations = (
        Observation.objects.filter(
            encounter=encounter,
        )
        .select_related("data_entered_by")
        .order_by("id")
    )

    medication_requests = (
        medication_request.MedicationRequest.objects.filter(encounter=encounter)
        .exclude(status=MedicationRequestStatus.entered_in_error.value)
        .select_related("created_by")
    )

    files = FileUpload.objects.filter(
        associating_id=encounter.external_id,
        upload_completed=True,
        is_archived=False,
    )

    admission_duration = (
        format_duration(
            parse_iso_datetime(encounter.period.get("end"))
            - parse_iso_datetime(encounter.period.get("start"))
        )
        if encounter.period.get("end", None) and encounter.period.get("start", None)
        else None
    )

    user_roles = {
        member["user_id"]: member["role"]["display"] for member in encounter.care_team
    }

    care_team_users = User.objects.filter(id__in=user_roles.keys())

    care_team_display = [
        f"{user.full_name} ({user_roles[user.id]})" for user in care_team_users
    ]

    return {
        "encounter": encounter,
        "admission_duration": admission_duration,
        "patient": encounter.patient,
        "symptoms": symptoms,
        "diagnoses": diagnoses,
        "principal_diagnosis": principal_diagnosis,
        "allergies": allergies,
        "observations": observations,
        "medication_requests": medication_requests,
        "files": files,
        "care_team": care_team_display,
        "discharge_summary_advice": encounter.discharge_summary_advice,
    }


def compile_typ(output_file, data):
    try:
        logo_path = (
            Path(settings.BASE_DIR)
            / "staticfiles"
            / "images"
            / "logos"
            / "black-logo.svg"
        )

        data["logo_path"] = "black-logo.svg"
        with tempfile.TemporaryDirectory() as tmpdir:
            template = Path(tmpdir) / "template.typ"
            template.write_text(
                render_to_string(
                    "reports/patient_discharge_summary_pdf_template.typ", context=data
                )
            )

            logo_dest = Path(tmpdir) / "black-logo.svg"
            logo_dest.write_text(logo_path.read_text())

            subprocess.run(  # noqa: S603
                [
                    settings.TYPST_BIN,
                    "compile",
                    str(template.name),
                    str(output_file),
                ],
                capture_output=True,
                check=True,
                shell=False,
                cwd=tmpdir,
            )

        logging.info(
            "Successfully Compiled Summary pdf for %s", data["encounter"].external_id
        )

    except subprocess.CalledProcessError as e:
        logging.error(
            "Error compiling summary pdf for %s: %s",
            data["encounter"].external_id,
            e.stderr.decode("utf-8"),
        )
        raise e


def generate_discharge_summary_pdf(data, file):
    logger.info(
        "Generating Discharge Summary pdf for %s", data["encounter"].external_id
    )
    compile_typ(output_file=file.name, data=data)
    logger.info(
        "Successfully Generated Discharge Summary pdf for %s",
        data["encounter"].external_id,
    )


def generate_and_upload_discharge_summary(encounter: Encounter):
    logger.info("Generating Discharge Summary for %s", encounter.external_id)

    set_lock(encounter.external_id, 5)
    try:
        current_date = timezone.now()
        timestamp = int(current_date.timestamp() * 1000)
        patient_name_slug: str = (
            encounter.patient.name.lower().strip().replace(" ", "_")
        )
        summary_file = FileUpload(
            name=f"discharge_summary-{patient_name_slug}-{int(timestamp)}",
            internal_name=f"{uuid4()}{int(time.time())}.pdf",
            file_type=FileTypeChoices.encounter.value,
            file_category=FileCategoryChoices.discharge_summary.value,
            associating_id=encounter.external_id,
        )

        set_lock(encounter.external_id, 10)
        data = get_discharge_summary_data(encounter)
        data["date"] = current_date

        set_lock(encounter.external_id, 50)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
            generate_discharge_summary_pdf(data, file)
            logger.info("Uploading Discharge Summary for %s", encounter.external_id)
            summary_file.files_manager.put_object(
                summary_file, file, ContentType="application/pdf"
            )
            summary_file.upload_completed = True
            summary_file.save(skip_internal_name=True)
            logger.info(
                "Uploaded Discharge Summary for %s, file id: %s",
                encounter.external_id,
                summary_file.id,
            )
    finally:
        clear_lock(encounter.external_id)

    return summary_file


def generate_discharge_report_signed_url(patient_external_id: str):
    encounter = (
        Encounter()
        .objects.filter(patient__external_id=patient_external_id)
        .order_by("-created_date")
        .first()
    )
    if not encounter:
        return None

    summary_file = generate_and_upload_discharge_summary(encounter)
    return summary_file.files_manager.signed_url(
        summary_file, duration=2 * 24 * 60 * 60
    )
