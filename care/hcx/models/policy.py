from django.db import models

from care.facility.models.patient import PatientRegistration
from care.hcx.models.base import (
    OUTCOME_CHOICES,
    PRIORITY_CHOICES,
    PURPOSE_CHOICES,
    STATUS_CHOICES,
)
from care.users.models import User
from care.utils.models.base import BaseModel


class Policy(BaseModel):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.CASCADE)

    subscriber_id = models.TextField(null=True, blank=True)
    policy_id = models.TextField(null=True, blank=True)

    insurer_id = models.TextField(null=True, blank=True)
    insurer_name = models.TextField(null=True, blank=True)

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
    purpose = models.CharField(
        choices=PURPOSE_CHOICES,
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
        related_name="policy_last_modified_by",
    )
