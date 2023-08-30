from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from care.abdm.models.base import (
    AccessMode,
    FrequencyUnit,
    HealthInformationTypes,
    Purpose,
    Status,
)
from care.abdm.models.json_schema import CARE_CONTEXTS, CONSENT_ARTEFACTS
from care.users.models import User
from care.utils.models.base import BaseModel
from care.utils.models.validators import JSONFieldSchemaValidator


class Consent(BaseModel):
    def default_expiry():
        return timezone.now() + timezone.timedelta(days=30)

    def default_from_time():
        return timezone.now() - timezone.timedelta(days=30)

    def default_to_time():
        return timezone.now()

    @property
    def request_id(self):
        return self.consent_id

    consent_id = models.UUIDField(null=True, blank=True)

    patient_health_id = models.CharField(max_length=50, null=True, blank=True)

    artefacts = models.JSONField(
        default=list, validators=[JSONFieldSchemaValidator(CONSENT_ARTEFACTS)]
    )
    care_contexts = models.JSONField(
        default=list, validators=[JSONFieldSchemaValidator(CARE_CONTEXTS)]
    )

    status = models.CharField(
        choices=Status.choices, max_length=20, default=Status.REQUESTED.value
    )
    purpose = models.CharField(
        choices=Purpose.choices, max_length=20, default=Purpose.CARE_MANAGEMENT.value
    )
    hi_types = ArrayField(
        models.CharField(choices=HealthInformationTypes.choices, max_length=20),
        default=list,
    )

    hip = models.CharField(max_length=50, null=True, blank=True)
    hiu = models.CharField(max_length=50, null=True, blank=True)
    cm = models.CharField(max_length=50, null=True, blank=True)

    requester = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    access_mode = models.CharField(
        choices=AccessMode.choices, max_length=20, default=AccessMode.VIEW.value
    )
    from_time = models.DateTimeField(null=True, blank=True, default=default_from_time)
    to_time = models.DateTimeField(null=True, blank=True, default=default_to_time)
    expiry = models.DateTimeField(null=True, blank=True, default=default_expiry)

    frequency_unit = models.CharField(
        choices=FrequencyUnit.choices, max_length=20, default=FrequencyUnit.HOUR.value
    )
    frequency_value = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    frequency_repeats = models.PositiveSmallIntegerField(default=0)
