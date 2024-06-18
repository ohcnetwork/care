from django.db import models

from care.facility.models import PatientBaseModel
from care.facility.models.mixins.permissions.patient import PatientPermissionMixin
from care.facility.models.patient import PatientRegistration
from care.users.models import User
from care.utils.models.base import BaseModel


class VaccineRegistration(BaseModel):
    name = models.CharField(max_length=200, blank=False, null=False)

    def __str__(self) -> str:
        return self.name


class PatientVaccination(PatientBaseModel):
    patient = models.ForeignKey(
        PatientRegistration,
        on_delete=models.PROTECT,
        null=True,
        related_name="vaccination_details",
    )
    vaccine_name = models.ForeignKey(
        VaccineRegistration, on_delete=models.PROTECT, null=False
    )
    last_vaccinated_date = models.DateField(null=False, blank=False)
    dose_number = models.PositiveIntegerField(default=1)
    vaccination_center = models.CharField(max_length=255, null=True, blank=True)
    batch_number = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vaccination_created_by",
    )
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vaccination_edited_by",
    )
