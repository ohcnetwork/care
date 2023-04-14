import tempfile
import time
from datetime import timedelta
from uuid import uuid4

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

    return {
        "patient": consultation.patient,
        "samples": samples,
        "hcx": hcx,
        "diagnosis": diagnosis,
        "provisional_diagnosis": provisional_diagnosis,
        "consultation": consultation,
        "dailyrounds": daily_rounds,
        "medical_history": medical_history,
        "investigations": investigations,
    }


def generate_discharge_summary_pdf(data, file):
    html_string = render_to_string("reports/patient_pdf_report.html", data)
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


@celery.task()
def generate_and_upload_discharge_summary(consultation_id):
    currnet_date = timezone.now()

    consultation = PatientConsultation.objects.get(external_id=consultation_id)

    file_db_entry: FileUpload = FileUpload.objects.create(
        name=f"discharge_summary-{consultation.patient.name}-{currnet_date}.pdf",
        internal_name=f"{uuid4()}.pdf",
        file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
        associating_id=consultation.external_id,
    )

    data = get_discharge_summary_data(consultation)
    data["date"] = currnet_date

    with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
        generate_discharge_summary_pdf(data, file)
        file_db_entry.put_object(file, ContentType="application/pdf")
        file_db_entry.upload_completed = True
        file_db_entry.save()

    return file_db_entry


@celery.task()
def email_discharge_summary(consultation_id, email):
    file = (
        FileUpload.objects.filter(
            file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
            associating_id=consultation_id,
        )
        .order_by("-created_date")
        .first()
    )

    if file and file.created_date <= timezone.now() - timedelta(minutes=2):
        # If the file is not uploaded in 10 minutes, delete the file and generate a new one
        file.delete()
        file = None

    if file is None:
        file = generate_and_upload_discharge_summary(consultation_id)
        time.sleep(2)

    if not file.upload_completed:
        # wait for file to be uploaded
        time.sleep(30)
        if file.upload_completed:
            file.refresh_from_db()
        else:
            return False

    msg = EmailMessage(
        "Patient Discharge Summary",
        "Please find the attached file",
        settings.DEFAULT_FROM_EMAIL,
        (email,),
    )
    msg.content_subtype = "html"
    msg.attach(file.name, file.get_content(), "application/pdf")
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
