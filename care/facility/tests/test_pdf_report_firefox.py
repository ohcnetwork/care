import tempfile
from uuid import uuid4
import pdfkit
import boto3
import celery
from django.conf import settings
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
    PrescriptionType,
)
from care.facility.models.file_upload import FileUpload
from care.facility.static_data.icd11 import get_icd11_diagnoses_objects_by_ids
from care.hcx.models.policy import Policy
from care.utils.csp import config as cs_provider


def get_discharge_summary_data(consultation: PatientConsultation):
    samples = PatientSample.objects.filter(
        patient=consultation.patient, consultation=consultation
    )
    hcx = Policy.objects.filter(patient=consultation.patient)
    daily_rounds = DailyRound.objects.filter(consultation=consultation)
    diagnosis = get_icd11_diagnoses_objects_by_ids(consultation.icd11_diagnoses)
    provisional_diagnosis = get_icd11_diagnoses_objects_by_ids(
        consultation.icd11_provisional_diagnoses
    )
    investigations = InvestigationValue.objects.filter(
        Q(consultation=consultation.id)
        & (Q(value__isnull=False) | Q(notes__isnull=False))
    )
    medical_history = Disease.objects.filter(patient=consultation.patient)
    prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.REGULAR.value,
        is_prn=False,
    )
    prn_prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.REGULAR.value,
        is_prn=True,
    )
    discharge_prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.DISCHARGE.value,
        is_prn=False,
    )
    discharge_prn_prescriptions = Prescription.objects.filter(
        consultation=consultation,
        prescription_type=PrescriptionType.DISCHARGE.value,
        is_prn=True,
    )

    return {
        "patient": consultation.patient,
        "samples": samples,
        "hcx": hcx,
        "diagnosis": diagnosis,
        "provisional_diagnosis": provisional_diagnosis,
        "consultation": consultation,
        "prescriptions": prescriptions,
        "prn_prescriptions": prn_prescriptions,
        "discharge_prescriptions": discharge_prescriptions,
        "discharge_prn_prescriptions": discharge_prn_prescriptions,
        "dailyrounds": daily_rounds,
        "medical_history": medical_history,
        "investigations": investigations,
    }


def generate_discharge_summary_pdf(data, file):
    html_string = render_to_string("reports/patient_pdf_report.html", data)
     pdfkit.from_string(html_string, file, options={"no-outline": None})


def generate_and_upload_discharge_summary(consultation_id):
    current_date = timezone.now()

    consultation = PatientConsultation.objects.get(external_id=consultation_id)

    file_db_entry = FileUpload.objects.create(
        name=f"discharge_summary-{consultation.patient.name}-{current_date}.pdf",
        internal_name=f"{uuid4()}.pdf",
        file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
        associating_id=consultation.external_id,
    )

    data = get_discharge_summary_data(consultation)
    data["date"] = current_date

    with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
        generate_discharge_summary_pdf(data, file)
        file_db_entry.put_object(file, ContentType="application/pdf")
        file_db_entry.upload_completed = True
        file_db_entry.save()

    return file_db_entry


@celery.task()
def generate_and_upload_discharge_summary_task(consultation_id):
    file_db_entry = generate_and_upload_discharge_summary(consultation_id)
    return file_db_entry.id


@celery.task()
def email_discharge_summary(consultation_id, email):
    generate_and_upload_discharge_summary_task(consultation_id)

    summary = (
        FileUpload.objects.filter(
            file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
            associating_id=consultation_id,
        )
        .order_by("-created_date")
        .first()
    )

    msg = EmailMessage(
        "Patient Discharge Summary",
        "Please find the attached file",
        settings.DEFAULT_FROM_EMAIL,
        (email,),
    )
    msg.content_subtype = "html"
    msg.attach(summary.name, summary.get_content(), "application/pdf")
    msg.send()

    return True


@celery.task()
def generate_discharge_report_signed_url(patient_external_id):
    consultation = (
        PatientConsultation.objects.filter(patient__external_id=patient_external_id)
        .order_by("-created_date")
        .first()
    )
    if not consultation:
        return None

    data = get_discharge_summary_data(consultation)

    signed_url = None
    with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
        generate_discharge_summary_pdf(data, file)
        s3 = boto3.client(
            "s3",
            **cs_provider.get_client_config(),
        )
        image_location = f"discharge_summary/{uuid4()}.pdf"
        s3.put_object(
            Bucket=settings.FILE_UPLOAD_BUCKET,
            Key=image_location,
            Body=file,
        )
        signed_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.FILE_UPLOAD_BUCKET,
                "Key": image_location,
            },
            ExpiresIn=2 * 24 * 60 * 60,  # seconds
        )
    return signed_url
