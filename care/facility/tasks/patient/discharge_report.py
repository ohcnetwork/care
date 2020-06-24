from io import BytesIO

import celery
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from easy_pdf.rendering import render_to_pdf

from care.facility.models import DailyRound, PatientConsultation, PatientRegistration, PatientSample


@celery.task()
def generate_discharge_report(patient, email):
    patient = PatientRegistration.objects.get(id=patient)
    consultation = PatientConsultation.objects.filter(patient=patient).order_by("-created_date")
    if consultation.exists():
        consultation = consultation.first()
        samples = PatientSample.objects.filter(patient=patient, consultation=consultation)
        daily_rounds = DailyRound.objects.filter(consultation=consultation)
    else:
        consultation = None
        samples = None
        daily_rounds = None
    content = render_to_pdf(
        "patient_pdf_template.html",
        {"patient": patient, "samples": samples, "consultation": consultation, "dailyround": daily_rounds},
    )
    msg = EmailMessage(
        "Patient Discharge Summary", "Please find the attached file", settings.DEFAULT_FROM_EMAIL, (email,),
    )

    file = File(BytesIO(content))

    msg.content_subtype = "html"  # Main content is now text/html
    msg.attach(patient.name + "-Discharge_Summary", file.read(), "application/pdf")
    msg.send()
