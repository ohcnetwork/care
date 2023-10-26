import enum

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField
from django.utils import timezone

from care.facility.models.patient_consultation import PatientConsultation
from care.utils.models.base import BaseModel


class FrequencyEnum(enum.Enum):
    STAT = "Immediately"
    OD = "once daily"
    HS = "Night only"
    BD = "Twice daily"
    TID = "8th hourly"
    QID = "6th hourly"
    Q4H = "4th hourly"
    QOD = "Alternate day"
    QWK = "Once a week"


class Routes(enum.Enum):
    ORAL = "Oral"
    IV = "IV"
    IM = "IM"
    SC = "S/C"


class PrescriptionType(enum.Enum):
    DISCHARGE = "DISCHARGE"
    REGULAR = "REGULAR"


def generate_choices(enum_class):
    return [(tag.name, tag.value) for tag in enum_class]


class MedibaseMedicineType(enum.Enum):
    BRAND = "brand"
    GENERIC = "generic"


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
        choices=generate_choices(MedibaseMedicineType),
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


class Prescription(BaseModel):
    consultation = models.ForeignKey(
        PatientConsultation,
        on_delete=models.PROTECT,
    )

    prescription_type = models.CharField(
        max_length=100,
        default=PrescriptionType.REGULAR.value,
        choices=generate_choices(PrescriptionType),
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
        choices=[(tag.name, tag.value) for tag in Routes],
        blank=True,
        null=True,
    )
    dosage = models.CharField(max_length=100, blank=True, null=True)

    is_prn = models.BooleanField(default=False)

    # non prn fields
    frequency = models.CharField(
        max_length=100,
        choices=[(tag.name, tag.value) for tag in FrequencyEnum],
        blank=True,
        null=True,
    )
    days = models.IntegerField(blank=True, null=True)

    # prn fields
    indicator = models.TextField(blank=True, null=True)
    max_dosage = models.CharField(max_length=100, blank=True, null=True)
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

    def __str__(self):
        return self.medicine + " - " + self.consultation.patient.name


class MedicineAdministration(BaseModel):
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

    def validate(self) -> None:
        if self.prescription.discontinued:
            raise ValidationError(
                {"prescription": "Prescription has been discontinued."}
            )

    def save(self, *args, **kwargs) -> None:
        self.validate()
        return super().save(*args, **kwargs)
