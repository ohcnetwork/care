from django.db import models
from django.utils.translation import gettext_lazy as _, gettext_lazy

from care.facility.models.mixins.permissions.patient import (
    ConsultationRelatedPermissionMixin,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.models.base import BaseModel


class ClinicalImpressionStatus(models.TextChoices):
    """
    See: https://fhir-ru.github.io/valueset-clinicalimpression-status.html
    """

    IN_PROGRESS = "in-progress", _("In Progress")
    COMPLETED = "completed", _("Completed")
    ENTERED_IN_ERROR = "entered-in-error", _("Entered in Error")


class Symptom(models.IntegerChoices):
    OTHERS = 9, gettext_lazy("Others")
    FEVER = 2, gettext_lazy("Fever")
    SORE_THROAT = 3, gettext_lazy("Sore Throat")
    COUGH = 4, gettext_lazy("Cough")
    BREATHLESSNESS = 5, gettext_lazy("Breathlessness")
    MYALGIA = 6, gettext_lazy("Myalgia")
    ABDOMINAL_DISCOMFORT = 7, gettext_lazy("Abdominal Discomfort")
    VOMITING = 8, gettext_lazy("Vomiting")
    SPUTUM = 11, gettext_lazy("Sputum")
    NAUSEA = 12, gettext_lazy("Nausea")
    CHEST_PAIN = 13, gettext_lazy("Chest Pain")
    HEMOPTYSIS = 14, gettext_lazy("Hemoptysis")
    NASAL_DISCHARGE = 15, gettext_lazy("Nasal Discharge")
    BODY_ACHE = 16, gettext_lazy("Body Ache")
    DIARRHOEA = 17, gettext_lazy("Diarrhoea")
    PAIN = 18, gettext_lazy("Pain")
    PEDAL_EDEMA = 19, gettext_lazy("Pedal Edema")
    WOUND = 20, gettext_lazy("Wound")
    CONSTIPATION = 21, gettext_lazy("Constipation")
    HEADACHE = 22, gettext_lazy("Headache")
    BLEEDING = 23, gettext_lazy("Bleeding")
    DIZZINESS = 24, gettext_lazy("Dizziness")
    CHILLS = 25, gettext_lazy("Chills")
    GENERAL_WEAKNESS = 26, gettext_lazy("General Weakness")
    IRRITABILITY = 27, gettext_lazy("Irritability")
    CONFUSION = 28, gettext_lazy("Confusion")
    ABDOMINAL_PAIN = 29, gettext_lazy("Abdominal Pain")
    JOINT_PAIN = 30, gettext_lazy("Joint Pain")
    REDNESS_OF_EYES = 31, gettext_lazy("Redness of Eyes")
    ANOREXIA = 32, gettext_lazy("Anorexia")
    NEW_LOSS_OF_TASTE = 33, gettext_lazy("New Loss of Taste")
    NEW_LOSS_OF_SMELL = 34, gettext_lazy("New Loss of Smell")


class EncounterSymptom(BaseModel, ConsultationRelatedPermissionMixin):
    symptom = models.SmallIntegerField(choices=Symptom, null=False, blank=False)
    other_symptom = models.CharField(default="", blank=True, null=False)
    onset_date = models.DateTimeField(null=False, blank=False)
    cure_date = models.DateTimeField(null=True, blank=True)
    clinical_impression_status = models.CharField(
        max_length=255,
        choices=ClinicalImpressionStatus,
        default=ClinicalImpressionStatus.IN_PROGRESS,
    )
    consultation = models.ForeignKey(
        PatientConsultation,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="symptoms",
    )
    created_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    updated_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    is_migrated = models.BooleanField(
        default=False,
        help_text="This field is to throw caution to data that was previously ported over",
    )

    def save(self, *args, **kwargs):
        if self.other_symptom and self.symptom != Symptom.OTHERS:
            msg = "Other Symptom should be empty when Symptom is not OTHERS"
            raise ValueError(msg)

        if self.clinical_impression_status != ClinicalImpressionStatus.ENTERED_IN_ERROR:
            if self.onset_date and self.cure_date:
                self.clinical_impression_status = ClinicalImpressionStatus.COMPLETED
            elif self.onset_date and not self.cure_date:
                self.clinical_impression_status = ClinicalImpressionStatus.IN_PROGRESS

        super().save(*args, **kwargs)
