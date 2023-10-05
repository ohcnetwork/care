import json
import logging
import tempfile
import time
from collections.abc import Iterable
from uuid import uuid4

import openai
from django.conf import settings
from django.core import serializers
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db.models import Q
from django.template import Context, Template
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

logger = logging.getLogger(__name__)

LOCK_DURATION = 10 * 60  # 10 minutes


def lock_key(consultation_ext_id: str):
    return f"discharge_summary_{consultation_ext_id}"


def set_lock(consultation_ext_id: str, progress: int):
    cache.set(lock_key(consultation_ext_id), progress, timeout=LOCK_DURATION)


def get_progress(consultation_ext_id: str):
    return cache.get(lock_key(consultation_ext_id))


def clear_lock(consultation_ext_id: str):
    cache.delete(lock_key(consultation_ext_id))


def get_discharge_summary_data(consultation: PatientConsultation):
    logger.info(f"fetching discharge summary data for {consultation.external_id}")
    samples = PatientSample.objects.filter(
        patient=consultation.patient, consultation=consultation
    )
    hcx = Policy.objects.filter(patient=consultation.patient)
    daily_rounds = DailyRound.objects.filter(consultation=consultation)
    diagnosis = get_icd11_diagnoses_objects_by_ids(consultation.icd11_diagnoses)
    provisional_diagnosis = get_icd11_diagnoses_objects_by_ids(
        consultation.icd11_provisional_diagnoses
    )
    principal_diagnosis = get_icd11_diagnoses_objects_by_ids(
        [consultation.icd11_principal_diagnosis]
        if consultation.icd11_principal_diagnosis
        else []
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
        "diagnosis": diagnosis,
        "provisional_diagnosis": provisional_diagnosis,
        "principal_diagnosis": principal_diagnosis,
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


def get_ai_response(prompt):
    openai.api_key = settings.OPENAI_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt},
        ],
        max_tokens=4096,
        temperature=0.5,
    )
    return response.choices[0].message.content


def generate_discharge_summary_pdf(data, file, is_ai, section_data):
    logger.info(
        f"Generating Discharge Summary html for {data['consultation'].external_id}"
    )
    logger.info(f"AI: {is_ai}\n Section Data: {section_data}")

    if is_ai:
        total_progress = 40
        current_progress = 0
        ai_data = {}
        data_resolved = {}
        for key, value in data.items():
            if isinstance(value, Iterable):
                if hasattr(value, "all"):
                    value = value.all()
                try:
                    data_resolved[key] = [
                        serializers.serialize(
                            "json",
                            [
                                x,
                            ],
                        )
                        for x in value
                    ]
                except:
                    try:
                        data_resolved[key] = [json.dumps(x) for x in value]
                    except:
                        data_resolved[key] = value

            else:
                data_resolved[key] = value

        summary_so_far = ""
        for i, section in enumerate(section_data.keys()):
            current_progress = (total_progress / len(section_data.keys())) * (i + 1)
            set_lock(data["consultation"].external_id, current_progress)
            t = Template(section_data[section])
            c = Context(data)
            json_data = t.render(c)

            if i == 0:
                prompt = f"""You are a healthcare AI tasked with generating a discharge summary for a patient. Given the patient details provided below, generate a summary of the data. Just output the summary directly. Strictly output just a summary and no extra data.
{section}
{json_data}
"""
            else:
                prompt = f"""You are a healthcare AI tasked with generating a discharge summary for a patient. Given the patient details provided below, generate a summary of the data. Strictly output just a summary and no extra data.
The following is a summary of the patient so far:
{summary_so_far}
With the above context, include the following information to the provided summary. Strictly output just a summary and no extra data.
{section}
{json_data}
"""
            logger.debug(prompt)

            section_summary = get_ai_response(prompt)
            ai_data[f"ai_summary_{section}"] = section_summary
            summary_so_far = section_summary
            time.sleep(10)

        combined_data = {
            **data,
            "ai_data": json.dumps(ai_data, indent=4).replace("\n", "<br>"),
        }

        combined_data["ai_summary"] = summary_so_far

        html_string = render_to_string(
            "reports/patient_ai_discharge_summary_pdf.html", combined_data
        )
    else:
        html_string = render_to_string(
            "reports/patient_discharge_summary_pdf.html", data
        )

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


def generate_and_upload_discharge_summary(
    consultation: PatientConsultation, section_data, is_ai=False
):
    logger.info(
        f"Generating Discharge Summary for {consultation.external_id} is_ai: {is_ai}"
    )

    set_lock(consultation.external_id, 5)
    try:
        current_date = timezone.now()
        summary_file = FileUpload(
            name=f"discharge_summary-{consultation.patient.name}-{current_date}.pdf",
            internal_name=f"{uuid4()}.pdf",
            file_type=FileUpload.FileType.DISCHARGE_SUMMARY.value,
            associating_id=consultation.external_id,
        )

        set_lock(consultation.external_id, 10)
        data = get_discharge_summary_data(consultation)
        data["date"] = current_date

        set_lock(consultation.external_id, 50)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
            generate_discharge_summary_pdf(data, file, is_ai, section_data)
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

    summary_file = generate_and_upload_discharge_summary(consultation, {}, False)
    return summary_file.read_signed_url(duration=2 * 24 * 60 * 60)
