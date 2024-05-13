import logging
import tempfile
from collections.abc import Iterable
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from hardcopy import bytestring_to_pdf

from care.facility.models import (
    DailyRound,
    Disease,
    InvestigationValue,
    PatientConsultation,
    PatientSample,
    Prescription,
    PrescriptionDosageType,
    PrescriptionType,
)
from care.facility.models.file_upload import FileUpload
from care.facility.models.icd11_diagnosis import (
    ACTIVE_CONDITION_VERIFICATION_STATUSES,
    ConditionVerificationStatus,
)
from care.facility.static_data.icd11 import get_icd11_diagnoses_objects_by_ids
from care.hcx.models.policy import Policy

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

    # retrieve diagnosis objects from in-memory table
    diagnoses = get_icd11_diagnoses_objects_by_ids([entry[0] for entry in entries])

    principal, unconfirmed, provisional, differential, confirmed = [], [], [], [], []

    for diagnosis, record in zip(diagnoses, entries):
        _, verification_status, is_principal = record
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


def get_discharge_summary_data(consultation: PatientConsultation):
    logger.info(f"fetching discharge summary data for {consultation.external_id}")
    samples = PatientSample.objects.filter(
        patient=consultation.patient, consultation=consultation
    )
    hcx = Policy.objects.filter(patient=consultation.patient)
    daily_rounds = DailyRound.objects.filter(consultation=consultation)
    diagnoses = get_diagnoses_data(consultation)
    investigations = InvestigationValue.objects.filter(
        Q(consultation=consultation.id)
        & (Q(value__isnull=False) | Q(notes__isnull=False))
    )
    medical_history = Disease.objects.filter(patient=consultation.patient)
    prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.REGULAR.value,
    ).exclude(dosage_type=PrescriptionDosageType.PRN.value)
    prn_prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.REGULAR.value,
        dosage_type=PrescriptionDosageType.PRN.value,
    )
    discharge_prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.DISCHARGE.value,
    ).exclude(dosage_type=PrescriptionDosageType.PRN.value)

    discharge_prn_prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.DISCHARGE.value,
        dosage_type=PrescriptionDosageType.PRN.value,
    )
    files = FileUpload.objects.filter(
        associating_id=consultation.id,
        file_type=FileUpload.FileType.CONSULTATION.value,
        upload_completed=True,
        is_archived=False,
    )

    return {
        "patient": consultation.patient,
        "samples": samples,
        "hcx": hcx,
        "principal_diagnoses": diagnoses["principal"],
        "unconfirmed_diagnoses": diagnoses["unconfirmed"],
        "provisional_diagnoses": diagnoses["provisional"],
        "differential_diagnoses": diagnoses["differential"],
        "confirmed_diagnoses": diagnoses["confirmed"],
        "consultation": consultation,
        "prescriptions": prescriptions,
        "prn_prescriptions": prn_prescriptions,
        "discharge_prescriptions": discharge_prescriptions,
        "discharge_prn_prescriptions": discharge_prn_prescriptions,
        "dailyrounds": daily_rounds,
        "medical_history": medical_history,
        "investigations": investigations,
        "files": files,
    }


def generate_discharge_summary_pdf(data, file):
    logger.info(
        f"Generating Discharge Summary html for {data['consultation'].external_id}"
    )
    html_string = render_to_string("reports/patient_discharge_summary_pdf.html", data)

    logger.info(
        f"Generating Discharge Summary pdf for {data['consultation'].external_id}"
    )
    bytestring_to_pdf(
        html_string.encode(),
        file,
        **{
            "no-margins": None,
            "disable-gpu": None,
            "disable-dev-shm-usage": False,
            "window-size": "2480,3508",
        },
    )


def generate_and_upload_discharge_summary(consultation: PatientConsultation):
    logger.info(f"Generating Discharge Summary for {consultation.external_id}")

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
            logger.info(f"Uploading Discharge Summary for {consultation.external_id}")
            summary_file.put_object(file, ContentType="application/pdf")
            summary_file.upload_completed = True
            summary_file.save()
            logger.info(
                f"Uploaded Discharge Summary for {consultation.external_id}, file id: {summary_file.id}"
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
