from django.db import models

from care.abdm.models.permissions.health_facility import HealthFacilityPermissions
from care.utils.models.base import BaseModel


class HealthFacility(BaseModel, HealthFacilityPermissions):
    hf_id = models.CharField(max_length=50, unique=True)
    registered = models.BooleanField(default=False)
    facility = models.OneToOneField(
        "facility.Facility", on_delete=models.PROTECT, to_field="external_id"
    )

    def __str__(self):
        return f"{self.hf_id} {self.facility}"
