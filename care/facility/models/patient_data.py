from types import SimpleNamespace

from django.db import models
from fernet_fields import EncryptedCharField
from multiselectfield import MultiSelectField
from simple_history.models import HistoricalRecords

from care.facility.models import District, FacilityBaseModel, LocalBody, SoftDeleteManager, State
from care.users.models import GENDER_CHOICES, User, phone_number_regex

DISEASE_CHOICES = [
    (1, "NO"),
    (2, "Diabetes"),
    (3, "Heart Disease"),
    (4, "HyperTension"),
    (5, "Kidney Diseases"),
]

SYMPTOM_CHOICES = [
    (1, "NO"),
    (2, "FEVER"),
    (3, "SORE THROAT"),
    (4, "COUGH"),
    (5, "BREATHLESSNESS"),
]

SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R")


class PatientRegistration(models.Model):
    facility = models.ForeignKey("Facility", on_delete=models.SET_NULL, null=True, default=True)

    name = EncryptedCharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    phone_number = EncryptedCharField(max_length=14, validators=[phone_number_regex])
    contact_with_carrier = models.BooleanField(verbose_name="Contact with a Covid19 carrier")

    local_body = models.ForeignKey(LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(
        default=True, help_text="Not active when discharged, or removed from the watchlist",
    )
    deleted = models.BooleanField(default=False)

    history = HistoricalRecords()

    objects = SoftDeleteManager()

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.age, self.get_gender_display())

    def delete(self, **kwargs):
        self.deleted = True
        self.save()

    @property
    def tele_consultation_history(self):
        return self.patientteleconsultation_set.order_by("-id")

    def save(self, *args, **kwargs) -> None:
        """
        While saving, if the local body is not null, then district will be local body's district
        Overriding save will help in a collision where the local body's district and district fields are different.
        """
        if self.local_body is not None:
            self.district = self.local_body.district
        if self.district is not None:
            self.state = self.district.state
        super().save(*args, **kwargs)


class Disease(models.Model):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.CASCADE, related_name="medical_history")
    disease = models.IntegerField(choices=DISEASE_CHOICES)
    details = models.TextField(blank=True, null=True)


class PatientTeleConsultation(models.Model):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.PROTECT)
    symptoms = MultiSelectField(choices=SYMPTOM_CHOICES)
    other_symptoms = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True, verbose_name="Reason for calling")
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class FacilityPatientStatsHistory(FacilityBaseModel):
    facility = models.ForeignKey("Facility", on_delete=models.PROTECT)
    entry_date = models.DateField()
    num_patients_visited = models.IntegerField(default=0)
    num_patients_home_quarantine = models.IntegerField(default=0)
    num_patients_isolation = models.IntegerField(default=0)
    num_patient_referred = models.IntegerField(default=0)

    class Meta:
        unique_together = (
            "facility",
            "entry_date",
        )


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
        "Facility", null=True, blank=True, on_delete=models.PROTECT, related_name="referred_patients",
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
