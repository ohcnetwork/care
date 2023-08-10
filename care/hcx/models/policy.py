from django.db import models

from care.facility.models.patient import PatientRegistration
from care.hcx.models.base import OutcomeEnum, PriorityEnum, PurposeEnum, StatusEnum
from care.users.models import User
from care.utils.models.base import BaseModel


class Policy(BaseModel):
    patient = models.ForeignKey(PatientRegistration, on_delete=models.CASCADE)

    subscriber_id = models.TextField(null=True, blank=True)
    policy_id = models.TextField(null=True, blank=True)

    insurer_id = models.TextField(null=True, blank=True)
    insurer_name = models.TextField(null=True, blank=True)

    status = models.CharField(
        choices=StatusEnum.choices, max_length=20, default=StatusEnum.ACTIVE.value
    )
    priority = models.CharField(
        choices=PriorityEnum.choices, max_length=20, default=PriorityEnum.NORMAL.value
    )
    purpose = models.CharField(
        choices=PurposeEnum.choices, max_length=20, default=PurposeEnum.BENEFITS.value
    )

    outcome = models.CharField(
        choices=OutcomeEnum.choices, max_length=20, default=None, blank=True, null=True
    )
    error_text = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="policy_last_modified_by",
    )
