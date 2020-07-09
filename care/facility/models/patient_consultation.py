from django.db import models
from multiselectfield import MultiSelectField

from care.facility.models import CATEGORY_CHOICES, PatientBaseModel
from care.facility.models.mixins.permissions.patient import PatientRelatedPermissionMixin
from care.facility.models.patient_base import ADMIT_CHOICES, CURRENT_HEALTH_CHOICES, SYMPTOM_CHOICES, SuggestionChoices
from care.users.models import User


class PatientConsultation(PatientBaseModel, PatientRelatedPermissionMixin):
    SUGGESTION_CHOICES = [
        (SuggestionChoices.HI, "HOME ISOLATION"),
        (SuggestionChoices.A, "ADMISSION"),
        (SuggestionChoices.R, "REFERRAL"),
        (SuggestionChoices.OP, "OP CONSULTATION"),
    ]

    patient = models.ForeignKey("PatientRegistration", on_delete=models.CASCADE, related_name="consultations")
    facility = models.ForeignKey("Facility", on_delete=models.CASCADE, related_name="consultations")
    symptoms = MultiSelectField(choices=SYMPTOM_CHOICES, default=1, null=True, blank=True)
    other_symptoms = models.TextField(default="", blank=True)
    symptoms_onset_date = models.DateTimeField(null=True, blank=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=8, default=None, blank=True, null=True)
    examination_details = models.TextField(null=True, blank=True)
    existing_medication = models.TextField(null=True, blank=True)
    prescribed_medication = models.TextField(null=True, blank=True)
    consultation_notes = models.TextField(null=True, blank=True)
    suggestion = models.CharField(max_length=4, choices=SUGGESTION_CHOICES)
    referred_to = models.ForeignKey(
        "Facility", null=True, blank=True, on_delete=models.PROTECT, related_name="referred_patients",
    )
    admitted = models.BooleanField(default=False)
    admitted_to = models.IntegerField(choices=ADMIT_CHOICES, default=None, null=True, blank=True)
    admission_date = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    bed_number = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.patient.name}<>{self.facility.name}"

    def save(self, *args, **kwargs):
        if not self.pk or self.referred_to is not None:
            # pk is None when the consultation is created
            # referred to is not null when the person is being referred to a new facility
            self.patient.facility = self.referred_to or self.facility
            self.patient.save()

        super(PatientConsultation, self).save(*args, **kwargs)

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


class DailyRound(PatientBaseModel):
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, related_name="daily_rounds")
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, default=0)
    temperature_measured_at = models.DateTimeField(null=True, blank=True)
    physical_examination_info = models.TextField(null=True, blank=True)
    additional_symptoms = MultiSelectField(choices=SYMPTOM_CHOICES, default=1, null=True, blank=True)
    other_symptoms = models.TextField(default="", blank=True)
    patient_category = models.CharField(choices=CATEGORY_CHOICES, max_length=8, default=None, blank=True, null=True)
    current_health = models.IntegerField(default=0, choices=CURRENT_HEALTH_CHOICES, blank=True)
    recommend_discharge = models.BooleanField(default=False, verbose_name="Recommend Discharging Patient")
    other_details = models.TextField(null=True, blank=True)

    @staticmethod
    def has_write_permission(request):
        return DailyRound.has_read_permission(request)

    @staticmethod
    def has_read_permission(request):
        return request.user.is_superuser or (
            (
                request.user
                in PatientConsultation.objects.get(
                    external_id=request.parser_context["kwargs"]["consultation_external_id"]
                ).facility.users.all()
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    request.user.district
                    == PatientConsultation.objects.get(
                        external_id=request.parser_context["kwargs"]["consultation_external_id"]
                    ).facility.district
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    request.user.state
                    == PatientConsultation.objects.get(
                        external_id=request.parser_context["kwargs"]["consultation_external_id"]
                    ).facility.state
                )
            )
        )

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or (self.consultation.patient.facility and request.user in self.consultation.patient.facility.users.all())
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.district == self.consultation.patient.facility.district
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.state == self.consultation.patient.facility.district
                )
            )
        )

    def has_object_write_permission(self, request):
        return self.has_object_read_permission(request)
