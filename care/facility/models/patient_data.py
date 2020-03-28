from types import SimpleNamespace

from django.db import models
from multiselectfield import MultiSelectField

from care.facility.models import SoftDeleteManager
from care.users.models import GENDER_CHOICES, User, phone_number_regex

MEDICAL_HISTORY_CHOICES = [
    (1, "NO"),
    (2, "Diabetes"),
    (3, "Heart Disease"),
    (4, "HyperTension"),
    (5, "Kidney Diseases"),
]

SYMPTOM_CHOICES = [(1, "NO"), (2, "FEVER"), (3, "SORE THROAT"), (4, "COUGH"), (5, "BREATHLESSNESS")]

SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R")


class PatientRegistration(models.Model):
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    phone_number = models.CharField(max_length=14, validators=[phone_number_regex], db_index=True)
    contact_with_carrier = models.BooleanField(verbose_name="Contact with a Covid19 carrier")
    medical_history = MultiSelectField(choices=MEDICAL_HISTORY_CHOICES, blank=False)
    medical_history_details = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True, help_text="Not active when discharged, or removed from the watchlist")
    deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.age, self.get_gender_display())

    def delete(self, **kwargs):
        self.deleted = True
        self.save()

    @property
    def tele_consultation_history(self):
        return self.patientteleconsultation_set.order_by("-id")


class PatientTeleConsultation(models.Model):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.PROTECT)
    symptoms = MultiSelectField(choices=SYMPTOM_CHOICES)
    other_symptoms = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True, verbose_name="Reason for calling")
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class PatientConsultation(models.Model):
    SUGGESTION_CHOICES = [
        (SuggestionChoices.HI, "HOME ISOLATION"),
        (SuggestionChoices.A, "ADMISSION"),
        (SuggestionChoices.R, "REFERRAL"),
    ]

    patient = models.ForeignKey(PatientRegistration, on_delete=models.CASCADE, related_name="consultations")
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, related_name="consultations")
    suggestion = models.CharField(max_length=3, choices=SUGGESTION_CHOICES)
    referred_to = models.ForeignKey(
        "Facility", null=True, blank=True, on_delete=models.PROTECT, related_name="referred_patients"
    )
    admitted = models.BooleanField(default=False)
    admission_date = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="if_referral_suggested",
                check=~models.Q(suggestion=SuggestionChoices.R) | models.Q(referred_to__isnull=False),
            ),
            models.CheckConstraint(
                name="if_admitted", check=models.Q(admitted=False) | models.Q(admission_date__isnull=False),
            ),
        ]
