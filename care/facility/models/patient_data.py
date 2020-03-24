from django.db import models
from multiselectfield import MultiSelectField

from care.users.models import GENDER_CHOICES, phone_number_regex, User

MEDICAL_HISTORY_CHOICES = [(1, "NO"), (2, "Diabetes"),
                           (3, "Heart Disease"), (4, "HyperTension"), (5, "Kidney Diseases")]

SYMPTOM_CHOICES = [(1, "NO"), (2, "FEVER"), (3, "SORE THROAT"), (4, "COUGH"), (5, "BREATHLESSNESS")]


class PatientRegistration(models.Model):
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    phone_number = models.CharField(max_length=14, validators=[phone_number_regex])
    contact_with_carrier = models.BooleanField(verbose_name="Contact with a Covid19 carrier")
    medical_history = MultiSelectField(choices=MEDICAL_HISTORY_CHOICES, blank=False)
    medical_history_details = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.age, self.get_gender_display())


class PatientTeleConsultation(models.Model):
    symptoms = MultiSelectField(choices=SYMPTOM_CHOICES)
    other_symptoms = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True, verbose_name="Reason for calling")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
