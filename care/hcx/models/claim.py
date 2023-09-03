from django.db import models
from django.db.models import JSONField

from care.facility.models.patient import PatientConsultation
from care.hcx.models.base import (
    CLAIM_TYPE_CHOICES,
    OUTCOME_CHOICES,
    PRIORITY_CHOICES,
    STATUS_CHOICES,
    USE_CHOICES,
)
from care.hcx.models.json_schema.claim import ITEMS
from care.hcx.models.policy import Policy
from care.users.models import User
from care.utils.models.base import BaseModel
from care.utils.models.validators import JSONFieldSchemaValidator


class Claim(BaseModel):
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.CASCADE)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
    )  # cascade - check it with Gigin

    items = JSONField(default=list, validators=[JSONFieldSchemaValidator(ITEMS)])
    total_claim_amount = models.FloatField(blank=True, null=True)
    total_amount_approved = models.FloatField(blank=True, null=True)

    use = models.CharField(
        choices=USE_CHOICES,
        max_length=20,
        default=None,
        blank=True,
        null=True,
    )
    status = models.CharField(
        choices=STATUS_CHOICES,
        max_length=20,
        default=None,
        blank=True,
        null=True,
    )
    priority = models.CharField(
        choices=PRIORITY_CHOICES,
        max_length=20,
        default="normal",
    )
    type = models.CharField(  # noqa: A003
        choices=CLAIM_TYPE_CHOICES,
        max_length=20,
        default=None,
        blank=True,
        null=True,
    )

    outcome = models.CharField(
        choices=OUTCOME_CHOICES,
        max_length=20,
        default=None,
        blank=True,
        null=True,
    )
    error_text = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="claim_last_modified_by",
    )
