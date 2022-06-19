"""
This suite of models intend to bring more structure towards the assocication of a patient with a facility,
Bed Models are connected from the patient model and is intended to efficiently manage facility assets and capacity
However this is an addon feature and is not required for the regular patient flow,
Leaving scope to build rooms and wards to being even more organization.
"""
import enum

from django.contrib.postgres.fields.jsonb import JSONField
from django.db import models

from care.facility.models.asset import Asset, AssetLocation
from care.facility.models.facility import Facility
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.models.base import BaseModel


class Bed(BaseModel):
    class BedType(enum.Enum):
        ISOLATION = 1
        ICU = 2
        ICU_WITH_NON_INVASIVE_VENTILATOR = 3
        ICU_WITH_OXYGEN_SUPPORT = 4
        ICU_WITH_INVASIVE_VENTILATOR = 5
        BED_WITH_OXYGEN_SUPPORT = 6
        REGULAR = 7

    BedTypeChoices = [(e.value, e.name) for e in BedType]

    name = models.CharField(max_length=1024)
    description = models.TextField(default="", blank=True)
    bed_type = models.IntegerField(choices=BedTypeChoices, default=BedType.REGULAR.value)
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, null=False, blank=False)  # Deprecated
    meta = JSONField(default=dict, blank=True)
    assets = models.ManyToManyField(Asset, through="AssetBed")
    location = models.ForeignKey(AssetLocation, on_delete=models.PROTECT, null=False, blank=False)

    def __str__(self):
        return self.name


class AssetBed(BaseModel):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=False, blank=False)
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, null=False, blank=False)
    meta = JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.asset.name} - {self.bed.name}"


class ConsultationBed(BaseModel):
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, null=False, blank=False)
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, null=False, blank=False)
    start_date = models.DateTimeField(null=False, blank=False)
    end_date = models.DateTimeField(null=True, blank=True, default=None)
    meta = JSONField(default=dict, blank=True)
