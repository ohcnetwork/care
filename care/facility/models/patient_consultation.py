from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import JSONField
from django.utils import timezone

from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    PatientBaseModel,
)
from care.facility.models.file_upload import FileUpload
from care.facility.models.mixins.permissions.patient import (
    ConsultationRelatedPermissionMixin,
)
from care.facility.models.patient_base import (
    DISCHARGE_REASON_CHOICES,
    NEW_DISCHARGE_REASON_CHOICES,
    REVERSE_CATEGORY_CHOICES,
    REVERSE_COVID_CATEGORY_CHOICES,
    RouteToFacility,
    SuggestionChoices,
    reverse_choices,
)
from care.users.models import User
from care.utils.models.base import BaseModel


class ConsentType(models.IntegerChoices):
    CONSENT_FOR_ADMISSION = 1, "Consent for Admission"
    PATIENT_CODE_STATUS = 2, "Patient Code Status"
    CONSENT_FOR_PROCEDURE = 3, "Consent for Procedure"
    HIGH_RISK_CONSENT = 4, "High Risk Consent"
    OTHERS = 5, "Others"


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
    deprecated_covid_category = models.CharField(
        choices=COVID_CATEGORY_CHOICES,
        max_length=8,
        default=None,
        blank=True,
        null=True,
    )  # Deprecated
    category = models.CharField(
        choices=CATEGORY_CHOICES, max_length=13, blank=False, null=True
    )
    examination_details = models.TextField(null=True, blank=True)
    history_of_present_illness = models.TextField(null=True, blank=True)
    treatment_plan = models.TextField(null=True, blank=True)
    consultation_notes = models.TextField(null=True, blank=True)
    course_in_facility = models.TextField(null=True, blank=True)
    investigation = JSONField(default=list)
    procedure = JSONField(default=dict)
    suggestion = models.CharField(max_length=4, choices=SUGGESTION_CHOICES)
    route_to_facility = models.SmallIntegerField(
        choices=RouteToFacility, blank=True, null=True
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
    previous_consultation = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
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

    has_consents = ArrayField(
        models.IntegerField(choices=ConsentType),
        default=list,
    )

    def get_related_consultation(self):
        return self

    CSV_MAPPING = {
        "consultation_created_date": "Date of Consultation",
        "encounter_date": "Date of Admission",
        "deprecated_symptoms_onset_date": "Date of Onset of Symptoms",
        "deprecated_symptoms": "Symptoms at time of consultation",
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
        if self.death_datetime and self.patient.death_datetime != self.death_datetime:
            self.patient.death_datetime = self.death_datetime
            self.patient.save(update_fields=["death_datetime"])
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="if_referral_suggested",
                condition=~models.Q(suggestion=SuggestionChoices.R)
                | models.Q(referred_to__isnull=False)
                | models.Q(referred_to_external__isnull=False),
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
            or (request.user in (self.assigned_to, self.patient.assigned_to))
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


class PatientCodeStatusType(models.IntegerChoices):
    NOT_SPECIFIED = 0, "Not Specified"
    DNH = 1, "Do Not Hospitalize"
    DNR = 2, "Do Not Resuscitate"
    COMFORT_CARE = 3, "Comfort Care Only"
    ACTIVE_TREATMENT = 4, "Active Treatment"


class ConsultationClinician(models.Model):
    consultation = models.ForeignKey(
        PatientConsultation,
        on_delete=models.PROTECT,
    )
    clinician = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
    )

    def __str__(self):
        return f"ConsultationClinician {self.consultation} - {self.clinician}"


class PatientConsent(BaseModel, ConsultationRelatedPermissionMixin):
    consultation = models.ForeignKey(
        PatientConsultation, on_delete=models.CASCADE, related_name="consents"
    )
    type = models.IntegerField(choices=ConsentType)
    patient_code_status = models.IntegerField(
        choices=PatientCodeStatusType, null=True, blank=True
    )
    archived = models.BooleanField(default=False)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="archived_consents",
    )
    archived_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_consents"
    )
    is_migrated = models.BooleanField(
        default=False,
        help_text="This field is to throw caution to data that was previously ported over",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["consultation", "type"],
                name="unique_consultation_consent",
                condition=models.Q(archived=False),
            ),
            models.CheckConstraint(
                name="patient_code_status_required",
                condition=~models.Q(type=ConsentType.PATIENT_CODE_STATUS)
                | models.Q(patient_code_status__isnull=False),
            ),
            models.CheckConstraint(
                name="patient_code_status_not_required",
                condition=models.Q(type=ConsentType.PATIENT_CODE_STATUS)
                | models.Q(patient_code_status__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.consultation.patient.name} - {ConsentType(self.type).label}{' (Archived)' if self.archived else ''}"

    def save(self, *args, **kwargs):
        if self.archived:
            files = FileUpload.objects.filter(
                associating_id=self.external_id,
                file_type=FileUpload.FileType.CONSENT_RECORD,
                is_archived=False,
            )
            files.update(
                is_archived=True,
                archived_datetime=timezone.now(),
                archive_reason="Consent Archived",
                archived_by=self.archived_by,
            )

        super().save(*args, **kwargs)

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
                self.consultation.patient.facility
                and request.user in self.consultation.patient.facility.users.all()
            )
            or (
                request.user
                in (
                    self.consultation.assigned_to,
                    self.consultation.patient.assigned_to,
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.district
                    == self.consultation.patient.facility.district
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.state == self.consultation.patient.facility.state
                )
            )
        )

    def has_object_update_permission(self, request):
        return super().has_object_update_permission(
            request
        ) and self.has_object_read_permission(request)
