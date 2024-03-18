from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import JSONField
from django.utils import timezone
from multiselectfield import MultiSelectField
from multiselectfield.utils import get_max_length

from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    PatientBaseModel,
)
from care.facility.models.mixins.permissions.patient import (
    ConsultationRelatedPermissionMixin,
)
from care.facility.models.patient_base import (
    DISCHARGE_REASON_CHOICES,
    NEW_DISCHARGE_REASON_CHOICES,
    REVERSE_CATEGORY_CHOICES,
    REVERSE_COVID_CATEGORY_CHOICES,
    SYMPTOM_CHOICES,
    RouteToFacility,
    SuggestionChoices,
    reverse_choices,
)
from care.users.models import User


class PatientConsultation(PatientBaseModel, ConsultationRelatedPermissionMixin):
    SUGGESTION_CHOICES = [
        (SuggestionChoices.HI, "HOME ISOLATION"),
        (SuggestionChoices.A, "ADMISSION"),
        (SuggestionChoices.R, "REFERRAL"),
        (SuggestionChoices.OP, "OP CONSULTATION"),
        (SuggestionChoices.DC, "DOMICILIARY CARE"),
        (SuggestionChoices.DD, "DECLARE DEATH"),
    ]
    REVERSE_SUGGESTION_CHOICES = reverse_choices(SUGGESTION_CHOICES)

    patient = models.ForeignKey(
        "PatientRegistration",
        on_delete=models.CASCADE,
        related_name="consultations",
    )

    patient_no = models.CharField(
        max_length=100,
        default=None,
        null=True,
        blank=True,
        help_text=(
            "Patient's unique number in the facility. "
            "IP number for inpatients and OP number for outpatients."
        ),
    )

    facility = models.ForeignKey(
        "Facility", on_delete=models.CASCADE, related_name="consultations"
    )
    deprecated_diagnosis = models.TextField(
        default="", null=True, blank=True
    )  # Deprecated
    deprecated_icd11_provisional_diagnoses = ArrayField(
        models.CharField(max_length=100), default=list, blank=True, null=True
    )  # Deprecated in favour of ConsultationDiagnosis M2M model
    deprecated_icd11_diagnoses = ArrayField(
        models.CharField(max_length=100), default=list, blank=True, null=True
    )  # Deprecated in favour of ConsultationDiagnosis M2M model
    deprecated_icd11_principal_diagnosis = models.CharField(
        max_length=100, default="", blank=True, null=True
    )  # Deprecated in favour of ConsultationDiagnosis M2M model
    symptoms = MultiSelectField(
        choices=SYMPTOM_CHOICES,
        default=1,
        null=True,
        blank=True,
        max_length=get_max_length(SYMPTOM_CHOICES, None),
    )
    other_symptoms = models.TextField(default="", blank=True)
    symptoms_onset_date = models.DateTimeField(null=True, blank=True)
    deprecated_covid_category = models.CharField(
        choices=COVID_CATEGORY_CHOICES,
        max_length=8,
        default=None,
        blank=True,
        null=True,
    )  # Deprecated
    category = models.CharField(
        choices=CATEGORY_CHOICES, max_length=8, blank=False, null=True
    )
    examination_details = models.TextField(null=True, blank=True)
    history_of_present_illness = models.TextField(null=True, blank=True)
    treatment_plan = models.TextField(null=True, blank=True)
    consultation_notes = models.TextField(null=True, blank=True)
    course_in_facility = models.TextField(null=True, blank=True)
    investigation = JSONField(default=dict)
    prescriptions = JSONField(default=dict)  # Deprecated
    procedure = JSONField(default=dict)
    suggestion = models.CharField(max_length=4, choices=SUGGESTION_CHOICES)
    route_to_facility = models.SmallIntegerField(
        choices=RouteToFacility.choices, blank=True, null=True
    )
    review_interval = models.IntegerField(default=-1)
    referred_to = models.ForeignKey(
        "Facility",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="referred_patients",
    )
    referred_to_external = models.TextField(default="", null=True, blank=True)
    transferred_from_location = models.ForeignKey(
        "AssetLocation",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    referred_from_facility = models.ForeignKey(
        "Facility",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    referred_from_facility_external = models.TextField(
        default="", null=True, blank=True
    )
    referred_by_external = models.TextField(default="", null=True, blank=True)
    is_readmission = models.BooleanField(default=False)
    admitted = models.BooleanField(default=False)  # Deprecated
    encounter_date = models.DateTimeField(default=timezone.now, db_index=True)
    icu_admission_date = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    discharge_reason = models.CharField(
        choices=DISCHARGE_REASON_CHOICES,
        max_length=4,
        default=None,
        blank=True,
        null=True,
    )
    new_discharge_reason = models.SmallIntegerField(
        choices=NEW_DISCHARGE_REASON_CHOICES,
        default=None,
        blank=True,
        null=True,
    )
    discharge_notes = models.TextField(default="", null=True, blank=True)
    discharge_prescription = JSONField(
        default=dict, null=True, blank=True
    )  # Deprecated
    discharge_prn_prescription = JSONField(
        default=dict, null=True, blank=True
    )  # Deprecated
    death_datetime = models.DateTimeField(null=True, blank=True)
    death_confirmed_doctor = models.TextField(default="", null=True, blank=True)
    bed_number = models.CharField(max_length=100, null=True, blank=True)  # Deprecated

    is_kasp = models.BooleanField(default=False)
    kasp_enabled_date = models.DateTimeField(null=True, blank=True, default=None)

    is_telemedicine = models.BooleanField(default=False)  # Deprecated
    last_updated_by_telemedicine = models.BooleanField(default=False)  # Deprecated

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="patient_assigned_to",
    )

    assigned_clinicians = models.ManyToManyField(
        User,
        related_name="patient_assigned_clinician",
        through="ConsultationClinician",
    )

    medico_legal_case = models.BooleanField(default=False)

    deprecated_verified_by = models.TextField(
        default="", null=True, blank=True
    )  # Deprecated
    treating_physician = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_user"
    )

    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="last_edited_user",
    )

    last_daily_round = models.ForeignKey(
        "facility.DailyRound",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
    )

    current_bed = models.ForeignKey(
        "facility.ConsultationBed",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )

    # Physical Information

    height = models.FloatField(
        default=None,
        null=True,
        verbose_name="Patient's Height in CM",
        validators=[MinValueValidator(0)],
    )
    weight = models.FloatField(
        default=None,
        null=True,
        verbose_name="Patient's Weight in KG",
        validators=[MinValueValidator(0)],
    )

    # ICU Information

    operation = models.TextField(default=None, null=True, blank=True)
    special_instruction = models.TextField(default=None, null=True, blank=True)

    # Intubation details

    intubation_history = JSONField(default=list)

    # Deprecated Fields

    prn_prescription = JSONField(default=dict)
    discharge_advice = JSONField(default=dict)

    def get_related_consultation(self):
        return self

    CSV_MAPPING = {
        "consultation_created_date": "Date of Consultation",
        "encounter_date": "Date of Admission",
        "symptoms_onset_date": "Date of Onset of Symptoms",
        "symptoms": "Symptoms at time of consultation",
        "deprecated_covid_category": "Covid Category",
        "category": "Category",
        "examination_details": "Examination Details",
        "suggestion": "Suggestion",
    }

    CSV_MAKE_PRETTY = {
        "deprecated_covid_category": (
            lambda x: REVERSE_COVID_CATEGORY_CHOICES.get(x, "-")
        ),
        "category": lambda x: REVERSE_CATEGORY_CHOICES.get(x, "-"),
        "suggestion": (
            lambda x: PatientConsultation.REVERSE_SUGGESTION_CHOICES.get(x, "-")
        ),
    }

    # CSV_DATATYPE_DEFAULT_MAPPING = {
    #     "encounter_date": (None, models.DateTimeField(),),
    #     "symptoms_onset_date": (None, models.DateTimeField(),),
    #     "symptoms": ("-", models.CharField(),),
    #     "category": ("-", models.CharField(),),
    #     "examination_details": ("-", models.CharField(),),
    #     "suggestion": ("-", models.CharField(),),
    # }

    def __str__(self):
        return f"{self.patient.name}<>{self.facility.name}"

    def save(self, *args, **kwargs):
        """
        # Removing Patient Hospital Change on Referral
        if not self.pk or self.referred_to is not None:
            # pk is None when the consultation is created
            # referred to is not null when the person is being referred to a new facility
            self.patient.facility = self.referred_to or self.facility
            self.patient.save()
        """
        super(PatientConsultation, self).save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="if_referral_suggested",
                check=~models.Q(suggestion=SuggestionChoices.R)
                | models.Q(referred_to__isnull=False)
                | models.Q(referred_to_external__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["patient_no", "facility"],
                name="unique_patient_no_within_facility",
                condition=models.Q(patient_no__isnull=False),
            ),
        ]

    @staticmethod
    def has_write_permission(request):
        return request.user.is_superuser or (
            request.user.verified
            and ConsultationRelatedPermissionMixin.has_write_permission(request)
        )

    def has_object_read_permission(self, request):
        if not super().has_object_read_permission(request):
            return False
        return (
            request.user.is_superuser
            or (
                self.patient.facility
                and request.user in self.patient.facility.users.all()
            )
            or (
                self.assigned_to == request.user
                or request.user == self.patient.assigned_to
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    self.patient.facility
                    and request.user.district == self.patient.facility.district
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    self.patient.facility
                    and request.user.state == self.patient.facility.state
                )
            )
        )

    def has_object_update_permission(self, request):
        return super().has_object_update_permission(
            request
        ) and self.has_object_read_permission(request)

    def has_object_discharge_patient_permission(self, request):
        return self.has_object_update_permission(request)

    def has_object_email_discharge_summary_permission(self, request):
        return self.has_object_read_permission(request)

    def has_object_generate_discharge_summary_permission(self, request):
        return self.has_object_read_permission(request)


class ConsultationClinician(models.Model):
    consultation = models.ForeignKey(
        PatientConsultation,
        on_delete=models.PROTECT,
    )
    clinician = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
    )
