from django.contrib.postgres.fields.jsonb import JSONField
from django.core.exceptions import ValidationError
from django.db import models
import enum

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

class Prescription(BaseModel):
    consultation = models.ForeignKey(
        PatientConsultation,
        on_delete=models.PROTECT,
    )
    medicine = models.CharField(max_length=100, blank=False, null=False)
    route = models.CharField(max_length=100, choices=[(tag.name, tag.value) for tag in Routes])
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100, choices=[(tag.name, tag.value) for tag in FrequencyEnum], blank=False, null=False)
    days = models.IntegerField()
    notes = models.TextField(default="", blank=True)
    meta = JSONField(default=dict, blank=True)
    prescribed_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
    )
    discontinued = models.BooleanField(default=False)
    discontinued_reason = models.TextField(default="", blank=True)
    discontinued_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.medicine + " - " + self.patient.name

class PRNPrescription(BaseModel):
    consultation = models.ForeignKey(
        PatientConsultation,
        on_delete=models.PROTECT,
    )
    medicine = models.CharField(max_length=100, blank=False, null=False)
    route = models.CharField(max_length=100, choices=[(tag.name, tag.value) for tag in Routes])
    dosage= models.CharField(max_length=100)
    indicator = models.TextField(blank=False, null=False)
    max_dosage = models.CharField(max_length=100)
    min_hours_between_doses = models.IntegerField()
    notes = models.TextField(default="", blank=True)
    meta = JSONField(default=dict, blank=True)
    prescribed_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
    )
    discontinued = models.BooleanField(default=False)
    discontinued_reason = models.TextField(default="", blank=True)
    discontinued_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.medicine + " - " + self.patient.name

class MedicineAdministration(BaseModel):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.PROTECT,
    )
    prn_prescription = models.ForeignKey(
        PRNPrescription,
        on_delete=models.PROTECT,
    )
    notes = models.TextField(default="", blank=True)
    administered_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
    )

    def __str__(self):
        return self.prescription.medicine + " - " + self.patient.name
    
    def validate(self) -> None:
        if (
            (not self.prescription and not self.prn_prescription) or 
            (self.prescription and self.prn_prescription)
        ):
            raise ValidationError(
                {"prescription": "Either prescription or prn_prescription is required."}
            )
        if (
            self.prescription and 
            self.prescription.discontinued
        ):
            raise ValidationError(
                {"prescription": "Prescription has been discontinued."}
            )
        if (
            self.prn_prescription and 
            self.prn_prescription.discontinued
        ):
            raise ValidationError(
                {"prn_prescription": "PRN Prescription has been discontinued."}
            )
        
    def save(self, *args, **kwargs) -> None:
        self.validate()
        return super().save(*args, **kwargs)