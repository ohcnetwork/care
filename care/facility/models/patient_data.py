from types import SimpleNamespace

from django.db import models
from fernet_fields import EncryptedCharField, EncryptedTextField
from multiselectfield import MultiSelectField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from care.facility.models import District, Facility, FacilityBaseModel, LocalBody, SoftDeleteManager, State
from care.users.models import GENDER_CHOICES, User, phone_number_regex

DISEASE_CHOICES = [
    (1, "NO"),
    (2, "Diabetes"),
    (3, "Heart Disease"),
    (4, "HyperTension"),
    (5, "Kidney Diseases"),
    (6, "Lung Diseases/Asthma"),
    (7, "Cancer"),
]

CATEGORY_CHOICES = [
    ("Mild", "Category-A"),
    ("Moderate", "Category-B"),
    ("Severe", "Category-C"),
    (None, "No Category"),
]

ADMIT_CHOICES = [
    (None, "Not admitted"),
    ("Admitted to", (
        (1, "Isolation Room"),
        (2, "ICU"),
        (3, "ICU with Ventilator"),
    )
    )
]

SYMPTOM_CHOICES = [
    (1, "NO"),
    (2, "FEVER"),
    (3, "SORE THROAT"),
    (4, "COUGH"),
    (5, "BREATHLESSNESS"),
    (6, "MYALGIA"),
    (7, "ABDOMINAL DISCOMFORT"),
    (8, "VOMITING/DIARRHOEA"),
    (9, "OTHERS")
]

DISEASE_STATUS_CHOICES = [
    (1, "SUSPECTED"),
    (2, "POSITIVE"),
    (3, "NEGATIVE"),
    (4, "RECOVERY"),
    (5, "RECOVERED"),
    (5, "EXPIRED"),
]

BLOOD_GROUP_CHOICES = [
    ("A+", "A+"),
    ("A-", "A-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("O+", "O+"),
    ("O-", "O-"),
]


SuggestionChoices = SimpleNamespace(HI="HI", A="A", R="R")


class PatientRegistration(models.Model):
    facility = models.ForeignKey("Facility", on_delete=models.SET_NULL, null=True)

    name = EncryptedCharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.IntegerField(choices=GENDER_CHOICES, blank=False)
    phone_number = EncryptedCharField(max_length=14, validators=[phone_number_regex])
    address = EncryptedTextField(default="")

    blood_group = models.CharField(choices=BLOOD_GROUP_CHOICES, null=True, blank=True, max_length=4)

    contact_with_confirmed_carrier = models.BooleanField(
        default=False, verbose_name="Confirmed Contact with a Covid19 Carrier"
    )
    contact_with_suspected_carrier = models.BooleanField(
        default=False, verbose_name="Suspected Contact with a Covid19 Carrier"
    )
    estimated_contact_date = models.DateTimeField(null=True, blank=True)

    past_travel = models.BooleanField(
        default=False, verbose_name="Travelled to Any Foreign Countries in the last 28 Days"
    )
    countries_travelled = models.TextField(default="", blank=True)
    date_of_return = models.DateTimeField(blank=True, null=True)

    present_health = models.TextField(default="", blank=True)
    has_SARI = models.BooleanField(default=False, verbose_name="Does the Patient Suffer from SARI")

    local_body = models.ForeignKey(LocalBody, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)

    disease_status = models.IntegerField(choices=DISEASE_STATUS_CHOICES, default=1, blank=True)

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

    @staticmethod
    def has_write_permission(request):
        return request.user.is_superuser or request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or request.user == self.created_by
            or (self.facility and request.user == self.facility.created_by)
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district == self.district
            )
        )

    def has_object_write_permission(self, request):
        return request.user.is_superuser

    def has_object_update_permission(self, request):
        return (
            request.user.is_superuser
            or request.user == self.created_by
            or (self.facility and request.user == self.facility.created_by)
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and request.user.district == self.district
            )
            #  TODO State Level Permissions
        )

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
    deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()

    class Meta:
        indexes = [PartialIndex(fields=["patient", "disease"], unique=True, where=PQ(deleted=False))]


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
    symptoms = MultiSelectField(choices=SYMPTOM_CHOICES, default=1)
    other_symptoms = models.TextField(blank=True, null=True)
    symptoms_onset_date = models.DateTimeField(null=True, blank=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=8, default=None)
    examination_details = models.TextField(null=True, blank=True)
    existing_medication = models.TextField(null=True, blank=True)
    prescribed_medication = models.TextField(null=True, blank=True)
    suggestion = models.CharField(max_length=3, choices=SUGGESTION_CHOICES)
    referred_to = models.ForeignKey(
        "Facility", null=True, blank=True, on_delete=models.PROTECT, related_name="referred_patients",
    )
    admitted = models.BooleanField(default=False)
    admitted_to = models.CharField(choices=ADMIT_CHOICES, max_length=1, default=None)
    admission_date = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.patient.name}<>{self.facility.name}"

    def save(self, *args, **kwargs):
        if not self.pk:  # will be true when the consultation is created
            self.patient.facility = self.facility
        super(PatientConsultation, self).save(*args, **kwargs)

    @staticmethod
    def has_write_permission(request):
        if not request.data.get("facility"):
            # Don't bother, the view shall raise a 400
            return True
        return request.user.is_superuser or (
            request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]
            and Facility.objects.get(id=request.data["facility"]).created_by == request.user
        )

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return request.user.is_superuser or request.user == self.facility.created_by

    def has_object_write_permission(self, request):
        return request.user.is_superuser

    def has_object_update_permission(self, request):
        return request.user == self.facility.created_by

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


class DailyRound(models.Model):
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, related_name="daily_rounds")
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, default=0)
    temperature_measured_at = models.DateTimeField(null=True, blank=True)
    physical_examination_info = models.TextField(null=True, blank=True)
    other_details = models.TextField(null=True, blank=True)

    @staticmethod
    def has_write_permission(request):
        return request.user.is_superuser or (
            request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]
            and (
                PatientConsultation.objects.get(
                    id=request.parser_context["kwargs"]["consultation_pk"]
                ).facility.created_by
                == request.user
            )
        )

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return request.user.is_superuser or request.user in (
            self.consultation.facility.created_by,
            self.consultation.patient.created_by,
        )

    def has_object_write_permission(self, request):
        return request.user.is_superuser or request.user in (
            self.consultation.facility.created_by,
            self.consultation.patient.created_by,
        )
