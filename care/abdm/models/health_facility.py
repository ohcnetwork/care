from django.db import models

from care.utils.models.base import BaseModel


class HealthFacility(BaseModel):
    hf_id = models.CharField(max_length=50, unique=True)
    facility = models.OneToOneField(
        "facility.Facility", on_delete=models.PROTECT, to_field="external_id"
    )

    def __str__(self):
        return self.hf_id + " " + self.facility.name
