# from django.db import models

# Create your models here.

from django.db import models

from care.abdm.permissions import HealthFacilityPermissions
from care.utils.models.base import BaseModel


class AbhaNumber(BaseModel):
    abha_number = models.TextField(null=True, blank=True)
    health_id = models.TextField(null=True, blank=True)

    name = models.TextField(null=True, blank=True)
    first_name = models.TextField(null=True, blank=True)
    middle_name = models.TextField(null=True, blank=True)
    last_name = models.TextField(null=True, blank=True)

    gender = models.TextField(null=True, blank=True)
    date_of_birth = models.TextField(null=True, blank=True)

    address = models.TextField(null=True, blank=True)
    district = models.TextField(null=True, blank=True)
    state = models.TextField(null=True, blank=True)
    pincode = models.TextField(null=True, blank=True)

    email = models.EmailField(null=True, blank=True)
    profile_photo = models.TextField(null=True, blank=True)

    new = models.BooleanField(default=False)

    txn_id = models.TextField(null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.abha_number


class HealthFacility(BaseModel, HealthFacilityPermissions):
    hf_id = models.CharField(max_length=50, unique=True)
    registered = models.BooleanField(default=False)
    facility = models.OneToOneField(
        "facility.Facility", on_delete=models.PROTECT, to_field="external_id"
    )

    def __str__(self):
        return self.hf_id + " " + self.facility.name
