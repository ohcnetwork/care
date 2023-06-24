import tempfile
from uuid import uuid4

import boto3
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage

from care.facility.models import PatientConsultation
from care.facility.models.file_upload import FileUpload
from care.facility.utils.reports.discharge_report import (
    generate_and_upload_discharge_summary,
    generate_discharge_summary_pdf,
    get_discharge_summary_data,
)
from care.utils.csp import config as cs_provider


@shared_task
def generate_and_upload_discharge_summary_task(consultation_id):
    file_db_entry = generate_and_upload_discharge_summary(consultation_id)
    return file_db_entry.id


@shared_task
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


@shared_task
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
