from django.db import models
from multiselectfield import MultiSelectField
from multiselectfield.utils import get_max_length

from care.facility.models import SymptomChoices, PatientRegistration
from care.users.models import User


class PatientTeleConsultation(models.Model):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.PROTECT)
    symptoms = MultiSelectField(
        choices=SymptomChoices.choices, max_length=get_max_length(SymptomChoices.choices, None)
    )
    other_symptoms = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True, verbose_name="Reason for calling")
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.patient.name + " on " + self.created_date.strftime("%d-%m-%Y")
