from django.db import models

from care.utils.models.base import BaseModel
from care.utils.models.validators import mobile_or_landline_number_validator


class PatientMobileOTP(BaseModel):
    is_used = models.BooleanField(default=False)
    phone_number = models.CharField(
        max_length=14, validators=[mobile_or_landline_number_validator]
    )
    otp = models.CharField(max_length=10)
