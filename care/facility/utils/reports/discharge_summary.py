import logging
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db.models import Case, IntegerField, Q, Value, When
from django.template.loader import render_to_string
from django.utils import timezone

from care.facility.models import (
    BedType,
    ConsultationBed,
    Disease,
    EncounterSymptom,
    InvestigationValue,
    PatientConsultation,
    PatientSample,
    Prescription,
    PrescriptionDosageType,
    PrescriptionType,
)
from care.facility.models.encounter_symptom import ClinicalImpressionStatus
from care.facility.models.file_upload import FileUpload
from care.facility.models.icd11_diagnosis import (
    ACTIVE_CONDITION_VERIFICATION_STATUSES,
    ConditionVerificationStatus,
)
from care.facility.static_data.icd11 import get_icd11_diagnosis_object_by_id

logger = logging.getLogger(__name__)

LOCK_DURATION = 2 * 60  # 2 minutes


def lock_key(consultation_ext_id: str):
    return f"discharge_summary_{consultation_ext_id}"


def set_lock(consultation_ext_id: str, progress: int):
    cache.set(lock_key(consultation_ext_id), progress, timeout=LOCK_DURATION)


def get_progress(consultation_ext_id: str):
    return cache.get(lock_key(consultation_ext_id))


def clear_lock(consultation_ext_id: str):
    cache.delete(lock_key(consultation_ext_id))


def get_diagnoses_data(consultation: PatientConsultation):
    entries = (
        consultation.diagnoses.filter(
            verification_status__in=ACTIVE_CONDITION_VERIFICATION_STATUSES
        )
        .order_by("-created_date")
        .values_list(
            "diagnosis_id",
            "verification_status",
            "is_principal",
        )
    )

    # retrieve diagnosis objects
    diagnoses = []
    for entry in entries:
        diagnose = get_icd11_diagnosis_object_by_id(entry[0])
        if diagnose:
            diagnoses.append(diagnose)
    principal, unconfirmed, provisional, differential, confirmed = [], [], [], [], []

    for diagnosis, record in zip(diagnoses, entries, strict=False):
        _, verification_status, is_principal = record

        diagnosis.verification_status = verification_status

        if is_principal:
            principal.append(diagnosis)
        if verification_status == ConditionVerificationStatus.UNCONFIRMED:
            unconfirmed.append(diagnosis)
        if verification_status == ConditionVerificationStatus.PROVISIONAL:
            provisional.append(diagnosis)
        if verification_status == ConditionVerificationStatus.DIFFERENTIAL:
            differential.append(diagnosis)
        if verification_status == ConditionVerificationStatus.CONFIRMED:
            confirmed.append(diagnosis)

    return {
        "principal": principal,
        "unconfirmed": unconfirmed,
        "provisional": provisional,
        "differential": differential,
        "confirmed": confirmed,
    }


def format_duration(duration):
    if not duration:
        return ""

    days = duration.days
    if days > 0:
        return f"{days} days"
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}"


def get_discharge_summary_data(consultation: PatientConsultation):
    logger.info("fetching discharge summary data for %s", consultation.external_id)
    samples = PatientSample.objects.filter(
        patient=consultation.patient, consultation=consultation
    )
    symptoms = EncounterSymptom.objects.filter(
        consultation=consultation, onset_date__lt=consultation.encounter_date
    ).exclude(clinical_impression_status=ClinicalImpressionStatus.ENTERED_IN_ERROR)
    diagnoses = get_diagnoses_data(consultation)
    investigations = InvestigationValue.objects.filter(
        Q(consultation=consultation.id)
        & (Q(value__isnull=False) | Q(notes__isnull=False))
    )
    medical_history = Disease.objects.filter(patient=consultation.patient)
    prescriptions = (
        Prescription.objects.filter(
            consultation=consultation, prescription_type=PrescriptionType.REGULAR.value
        )
        .annotate(
            order_priority=Case(
                When(dosage_type=PrescriptionDosageType.PRN.value, then=Value(2)),
                When(dosage_type=PrescriptionDosageType.TITRATED.value, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("order_priority", "id")
    )
    discharge_prescriptions = (
        Prescription.objects.filter(
            consultation=consultation,
            prescription_type=PrescriptionType.DISCHARGE.value,
        )
        .annotate(
            order_priority=Case(
                When(dosage_type=PrescriptionDosageType.PRN.value, then=Value(2)),
                When(dosage_type=PrescriptionDosageType.TITRATED.value, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("order_priority", "id")
    )
    files = FileUpload.objects.filter(
        associating_id=consultation.id,
        file_type=FileUpload.FileType.CONSULTATION.value,
        upload_completed=True,
        is_archived=False,
    )
    admitted_to = set()
    if ConsultationBed.objects.filter(consultation=consultation).exists():
        for bed in ConsultationBed.objects.filter(consultation=consultation).order_by(
            "-created_date"
        ):
            admitted_to.add(BedType(bed.bed.bed_type).name)
        admitted_to = list(admitted_to)
    if not admitted_to:
        admitted_to = None

    admission_duration = (
        format_duration(consultation.discharge_date - consultation.encounter_date)
        if consultation.discharge_date
        else None
    )

    return {
        "patient": consultation.patient,
        "samples": samples,
        "symptoms": symptoms,
        "admitted_to": admitted_to,
        "admission_duration": admission_duration,
        "diagnoses": diagnoses["confirmed"]
        + diagnoses["provisional"]
        + diagnoses["unconfirmed"]
        + diagnoses["differential"],
        "primary_diagnoses": diagnoses["principal"],
        "consultation": consultation,
        "prescriptions": prescriptions,
        "discharge_prescriptions": discharge_prescriptions,
        "medical_history": medical_history,
        "investigations": investigations,
        "files": files,
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

        data["logo_path"] = str(logo_path)

        content = render_to_string(
            "reports/patient_discharge_summary_pdf_template.typ", context=data
        )

        subprocess.run(  # noqa: S603
            [  # noqa: S607
                "typst",
                "compile",
                "-",
                str(output_file),
            ],
            input=content.encode("utf-8"),
            capture_output=True,
            check=True,
            cwd="/",
        )

        logging.info(
            "Successfully Compiled Summary pdf for %s", data["consultation"].external_id
        )
        return True

    except subprocess.CalledProcessError as e:
        logging.error(
            "Error compiling summary pdf for %s: %s",
            data["consultation"].external_id,
            e.stderr.decode("utf-8"),
        )
        return False


def generate_discharge_summary_pdf(data, file):
    logger.info(
        "Generating Discharge Summary pdf for %s", data["consultation"].external_id
    )
    compile_typ(output_file=file.name, data=data)
    logger.info(
        "Successfully Generated Discharge Summary pdf for %s",
        data["consultation"].external_id,
    )


def generate_and_upload_discharge_summary(consultation: PatientConsultation):
    logger.info("Generating Discharge Summary for %s", consultation.external_id)

    set_lock(consultation.external_id, 5)
    try:
        current_date = timezone.now()
        summary_file = FileUpload(
            name=f"discharge_summary-{consultation.patient.name}-{current_date}",
            internal_name=f"{uuid4()}.pdf",
            file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
            associating_id=consultation.external_id,
        )

        set_lock(consultation.external_id, 10)
        data = get_discharge_summary_data(consultation)
        data["date"] = current_date

        set_lock(consultation.external_id, 50)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
            generate_discharge_summary_pdf(data, file)
            logger.info("Uploading Discharge Summary for %s", consultation.external_id)
            summary_file.put_object(file, ContentType="application/pdf")
            summary_file.upload_completed = True
            summary_file.save()
            logger.info(
                "Uploaded Discharge Summary for %s, file id: %s",
                consultation.external_id,
                summary_file.id,
            )
    finally:
        clear_lock(consultation.external_id)

    return summary_file


def email_discharge_summary(summary_file: FileUpload, emails: Iterable[str]):
    msg = EmailMessage(
        "Patient Discharge Summary",
        "Please find the attached file",
        settings.DEFAULT_FROM_EMAIL,
        emails,
    )
    msg.content_subtype = "html"
    _, data = summary_file.file_contents()
    msg.attach(summary_file.name, data, "application/pdf")
    return msg.send()


def generate_discharge_report_signed_url(patient_external_id: str):
    consultation = (
        PatientConsultation.objects.filter(patient__external_id=patient_external_id)
        .order_by("-created_date")
        .first()
    )
    if not consultation:
        return None

    summary_file = generate_and_upload_discharge_summary(consultation)
    return summary_file.read_signed_url(duration=2 * 24 * 60 * 60)
