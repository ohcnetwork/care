from django.db import models
from django.utils.translation import gettext_lazy as _

from care.facility.models.mixins.permissions.patient import (
    ConsultationRelatedPermissionMixin,
)
from care.facility.models.patient_base import reverse_choices
from care.utils.models.base import BaseModel


class ICD11ClassKind(models.TextChoices):
    CHAPTER = "chapter"
    BLOCK = "block"
    CATEGORY = "category"


class ICD11Diagnosis(models.Model):
    """
    Use ICDDiseases for in-memory search.
    """

    id = models.BigIntegerField(primary_key=True)
    icd11_id = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255)
    class_kind = models.CharField(max_length=255, choices=ICD11ClassKind.choices)
    is_leaf = models.BooleanField()
    parent = models.ForeignKey("self", on_delete=models.DO_NOTHING, null=True)
    average_depth = models.IntegerField()
    is_adopted_child = models.BooleanField()
    breadth_value = models.DecimalField(max_digits=24, decimal_places=22)

    # Meta fields
    meta_hidden = models.BooleanField(default=False)
    meta_chapter = models.CharField(max_length=255)
    meta_chapter_short = models.CharField(max_length=255, null=True)
    meta_root_block = models.CharField(max_length=255, null=True)
    meta_root_category = models.CharField(max_length=255, null=True)

    def __str__(self) -> str:
        return self.label


class ConditionVerificationStatus(models.TextChoices):
    """
    See: https://www.hl7.org/fhir/valueset-condition-ver-status.html
    """

    UNCONFIRMED = "unconfirmed", _("Unconfirmed")
    PROVISIONAL = "provisional", _("Provisional")
    DIFFERENTIAL = "differential", _("Differential")
    CONFIRMED = "confirmed", _("Confirmed")
    REFUTED = "refuted", _("Refuted")
    ENTERED_IN_ERROR = "entered-in-error", _("Entered in Error")


INACTIVE_CONDITION_VERIFICATION_STATUSES = [
    ConditionVerificationStatus.REFUTED,
    ConditionVerificationStatus.ENTERED_IN_ERROR,
]  # Theses statuses are not allowed to be selected during create or can't be a principal diagnosis

ACTIVE_CONDITION_VERIFICATION_STATUSES = [
    status
    for status in ConditionVerificationStatus
    if status not in INACTIVE_CONDITION_VERIFICATION_STATUSES
]  # These statuses are allowed to be selected during create and these diagnosis can only be a principal diagnosis

REVERSE_CONDITION_VERIFICATION_STATUSES = reverse_choices(
    [(x.value, str(x.label)) for x in ConditionVerificationStatus]
)


class ConsultationDiagnosis(BaseModel, ConsultationRelatedPermissionMixin):
    consultation = models.ForeignKey(
        "PatientConsultation", on_delete=models.CASCADE, related_name="diagnoses"
    )
    diagnosis = models.ForeignKey(ICD11Diagnosis, on_delete=models.PROTECT)
    verification_status = models.CharField(
        max_length=20, choices=ConditionVerificationStatus.choices
    )
    is_principal = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    is_migrated = models.BooleanField(
        default=False,
        help_text="This field is to throw caution to data that was previously ported over",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["consultation", "diagnosis"],
                name="unique_diagnosis_per_consultation",
            ),
            # A consultation can have only one principal diagnosis
            # in other words: unique together (consultation, is_principal) where is_principal is true
            models.UniqueConstraint(
                fields=["consultation", "is_principal"],
                condition=models.Q(is_principal=True),
                name="unique_principal_diagnosis",
            ),
            # Diagnosis cannot be principal if verification status is one of refuted/entered-in-error.
            models.CheckConstraint(
                condition=(
                    models.Q(is_principal=False)
                    | ~models.Q(
                        verification_status__in=INACTIVE_CONDITION_VERIFICATION_STATUSES
                    )
                ),
                name="refuted_or_entered_in_error_diagnosis_cannot_be_principal",
            ),
        ]
