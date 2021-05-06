import datetime
import random
import string
import time

import celery
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.timezone import make_aware
from hardcopy import bytestring_to_pdf

from care.facility.models import DailyRound, PatientConsultation, PatientRegistration, PatientSample, Disease


def randomString(stringLength):
    letters = string.ascii_letters
    return "".join(random.choice(letters) for i in range(stringLength))


@celery.task()
def generate_discharge_report(patient_id, email):
    patient = PatientRegistration.objects.get(id=patient_id)
    consultation = PatientConsultation.objects.filter(patient=patient).order_by("-created_date")
    diseases = Disease.objects.filter(patient=patient)
    if consultation.exists():
        consultation = consultation.first()
        samples = PatientSample.objects.filter(patient=patient, consultation=consultation)
        daily_rounds = DailyRound.objects.filter(consultation=consultation)
    else:
        consultation = None
        samples = None
        daily_rounds = None
    date = make_aware(datetime.datetime.now())
    html_string = render_to_string(
        "patient_pdf_template.html",
        {
            "patient": patient,
            "samples": samples,
            "consultation": consultation,
            "dailyrounds": daily_rounds,
            "date": date,
            "diseases": diseases,
        },
    )
    filename = str(int(round(time.time() * 1000))) + randomString(10) + ".pdf"
    bytestring_to_pdf(
        html_string.encode(),
        default_storage.open(filename, "w+"),
        **{"no-margins": None, "disable-gpu": None, "disable-dev-shm-usage": False, "window-size": "2480,3508"},
    )
    file = default_storage.open(filename, "rb")
    msg = EmailMessage(
        "Patient Discharge Summary", "Please find the attached file", settings.DEFAULT_FROM_EMAIL, (email,),
    )
    msg.content_subtype = "html"  # Main content is now text/html
    msg.attach(patient.name + "-Discharge_Summary.pdf", file.read(), "application/pdf")
    msg.send()
    default_storage.delete(filename)
