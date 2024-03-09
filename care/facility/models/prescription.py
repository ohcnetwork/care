from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from care.facility.models.mixins.permissions.patient import (
    ConsultationRelatedPermissionMixin,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.models.base import BaseModel
from care.utils.models.validators import dosage_validator


# class FrequencyEnum(enum.Enum):
#     STAT = "Immediately"
#     OD = "once daily"
#     HS = "Night only"
#     BD = "Twice daily"
#     TID = "8th hourly"
#     QID = "6th hourly"
#     Q4H = "4th hourly"
#     QOD = "Alternate day"
#     QWK = "Once a week"
#
#
# class Routes(enum.Enum):
#     ORAL = "Oral"
#     IV = "IV"
#     IM = "IM"
#     SC = "S/C"
#     INHALATION = "Inhalation"
#     NASOGASTRIC = "Nasogastric/Gastrostomy tube"
#     INTRATHECAL = "intrathecal injection"
#     TRANSDERMAL = "Transdermal"
#     RECTAL = "Rectal"
#
#
# class PrescriptionType(enum.Enum):
#     DISCHARGE = "DISCHARGE"
#     REGULAR = "REGULAR"
#
#
# def generate_choices(enum_class):
#     return [(tag.name, tag.value) for tag in enum_class]
#
#
# class MedibaseMedicineType(enum.Enum):
#     BRAND = "brand"
#     GENERIC = "generic"

class FrequencyChoices(models.TextChoices):
    STAT = "STAT", _("Immediately")
    OD = "OD", _("Once daily")
    HS = "HS", _("Night only")
    BD = "BD", _("Twice daily")
    TID = "TID", _("8th hourly")
    QID = "QID", _("6th hourly")
    Q4H = "Q4H", _("4th hourly")
    QOD = "QOD", _("Alternate day")
    QWK = "QWK", _("Once a week")


class RoutesChoices(models.TextChoices):
    ORAL = "ORAL", _("Oral")
    IV = "IV", _("IV")
    IM = "IM", _("IM")
    SC = "SC", _("S/C")
    INHALATION = "INHALATION", _("Inhalation")
    NASOGASTRIC = "NASOGASTRIC", _("Nasogastric/Gastrostomy tube")
    INTRATHECAL = "INTRATHECAL", _("Intrathecal injection")
    TRANSDERMAL = "TRANSDERMAL", _("Transdermal")
    RECTAL = "RECTAL", _("Rectal")


class PrescriptionType(models.TextChoices):
    DISCHARGE = "DISCHARGE", _("Discharge")
    REGULAR = "REGULAR", _("Regular")


class MedibaseMedicineType(models.TextChoices):
    BRAND = "BRAND", _("Brand")
    GENERIC = "GENERIC", _("Generic")


class MedibaseMedicine(BaseModel):
    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        db_index=True,
        unique=True,
    )
    type = models.CharField(
        max_length=16,
        choices=MedibaseMedicineType.choices,
        blank=False,
        null=False,
        db_index=True,
    )
    generic = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    company = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    contents = models.TextField(blank=True, null=True)
    cims_class = models.CharField(max_length=255, blank=True, null=True)
    atc_classification = models.TextField(blank=True, null=True)

    def __str__(self):
        return " - ".join(filter(None, [self.name, self.generic, self.company]))


class Prescription(BaseModel, ConsultationRelatedPermissionMixin):
    consultation = models.ForeignKey(
        PatientConsultation,
        on_delete=models.PROTECT,
    )

    prescription_type = models.CharField(
        max_length=100,
        default=PrescriptionType.REGULAR.value,
        choices=PrescriptionType.choices,
    )

    medicine = models.ForeignKey(
        MedibaseMedicine,
        on_delete=models.PROTECT,
        null=True,
        blank=False,
    )
    medicine_old = models.CharField(max_length=1023, blank=False, null=True)
    route = models.CharField(
        max_length=100,
        choices=RoutesChoices.choices,
        blank=True,
        null=True,
    )
    dosage = models.CharField(
        max_length=100, blank=True, null=True, validators=[dosage_validator]
    )

    is_prn = models.BooleanField(default=False)

    # non prn fields
    frequency = models.CharField(
        max_length=100,
        choices=FrequencyChoices.choices,
        blank=True,
        null=True,
    )
    days = models.IntegerField(blank=True, null=True)

    # prn fields
    indicator = models.TextField(blank=True, null=True)
    max_dosage = models.CharField(
        max_length=100, blank=True, null=True, validators=[dosage_validator]
    )
    min_hours_between_doses = models.IntegerField(blank=True, null=True)

    notes = models.TextField(default="", blank=True)
    meta = JSONField(default=dict, blank=True)
    prescribed_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
    )
    discontinued = models.BooleanField(default=False)
    discontinued_reason = models.TextField(default="", blank=True)
    discontinued_date = models.DateTimeField(null=True, blank=True)

    is_migrated = models.BooleanField(
        default=False
    )  # This field is to throw caution to data that was previously ported over

    def save(self, *args, **kwargs) -> None:
        # check if prescription got discontinued just now
        if not self.is_migrated:
            if self.discontinued and not self.discontinued_date:
                self.discontinued_date = timezone.now()
            if not self.discontinued and self.discontinued_date:
                self.discontinued_date = None
        return super().save(*args, **kwargs)

    @property
    def medicine_name(self):
        return str(self.medicine) if self.medicine else self.medicine_old

    def has_object_write_permission(self, request):
        return ConsultationRelatedPermissionMixin.has_write_permission(request)

    def __str__(self):
        return self.medicine + " - " + self.consultation.patient.name


class MedicineAdministration(BaseModel, ConsultationRelatedPermissionMixin):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.PROTECT,
        related_name="administrations",
    )
    notes = models.TextField(default="", blank=True)
    administered_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
    )
    administered_date = models.DateTimeField(
        null=False, blank=False, default=timezone.now
    )
    archived_on = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        related_name="+",
    )

    def __str__(self):
        return (
            self.prescription.medicine
            + " - "
            + self.prescription.consultation.patient.name
        )

    def get_related_consultation(self):
        return self.prescription.consultation

    def has_object_write_permission(self, request):
        return ConsultationRelatedPermissionMixin.has_write_permission(request)

    def validate(self) -> None:
        if self.prescription.discontinued:
            raise ValidationError(
                {"prescription": "Prescription has been discontinued."}
            )

    def save(self, *args, **kwargs) -> None:
        self.validate()
        return super().save(*args, **kwargs)
