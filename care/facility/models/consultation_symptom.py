from django.db import models
from django.utils.translation import gettext_lazy as _

from care.facility.models.daily_round import DailyRound
from care.facility.models.mixins.permissions.patient import (
    ConsultationRelatedPermissionMixin,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.models.base import BaseModel


class Symptom(models.TextChoices):
    ASYMPTOMATIC = "ASYMPTOMATIC", _("Asymptomatic")
    FEVER = "FEVER", _("Fever")
    SORE_THROAT = "SORE THROAT", _("Sore Throat")
    COUGH = "COUGH", _("Cough")
    BREATHLESSNESS = "BREATHLESSNESS", _("Breathlessness")
    MYALGIA = "MYALGIA", _("Myalgia")
    ABDOMINAL_DISCOMFORT = "ABDOMINAL DISCOMFORT", _("Abdominal Discomfort")
    VOMITING = "VOMITING", _("Vomiting")
    OTHERS = "OTHERS", _("Others")
    SPUTUM = "SPUTUM", _("Sputum")
    NAUSEA = "NAUSEA", _("Nausea")
    CHEST_PAIN = "CHEST PAIN", _("Chest Pain")
    HEMOPTYSIS = "HEMOPTYSIS", _("Hemoptysis")
    NASAL_DISCHARGE = "NASAL DISCHARGE", _("Nasal Discharge")
    BODY_ACHE = "BODY ACHE", _("Body Ache")
    DIARRHOEA = "DIARRHOEA", _("Diarrhoea")
    PAIN = "PAIN", _("Pain")
    PEDAL_EDEMA = "PEDAL EDEMA", _("Pedal Edema")
    WOUND = "WOUND", _("Wound")
    CONSTIPATION = "CONSTIPATION", _("Constipation")
    HEAD_ACHE = "HEAD ACHE", _("Head Ache")
    BLEEDING = "BLEEDING", _("Bleeding")
    DIZZINESS = "DIZZINESS", _("Dizziness")
    CHILLS = "CHILLS", _("Chills")
    GENERAL_WEAKNESS = "GENERAL WEAKNESS", _("General Weakness")
    IRRITABILITY = "IRRITABILITY", _("Irritability")
    CONFUSION = "CONFUSION", _("Confusion")
    ABDOMINAL_PAIN = "ABDOMINAL PAIN", _("Abdominal Pain")
    JOINT_PAIN = "JOINT PAIN", _("Joint Pain")
    REDNESS_OF_EYES = "REDNESS OF EYES", _("Redness of Eyes")
    ANOREXIA = "ANOREXIA", _("Anorexia")
    NEW_LOSS_OF_TASTE = "NEW LOSS OF TASTE", _("New Loss of Taste")
    NEW_LOSS_OF_SMELL = "NEW LOSS OF SMELL", _("New Loss of Smell")


class ConsultationSymptom(BaseModel, ConsultationRelatedPermissionMixin):
    symptom = models.CharField(choices=Symptom.choices, blank=True)
    other_symptom = models.CharField(default="", blank=True)
    onset_date = models.DateTimeField(null=True, blank=True)
    cure_date = models.DateTimeField(null=True, blank=True)
    consultation = models.ForeignKey(
        PatientConsultation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="symptoms_timeline",
    )
    daily_round = models.ForeignKey(
        DailyRound,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="daily_round_symptoms",
    )
