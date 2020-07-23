import datetime
import enum

from django.db import models
from fernet_fields import EncryptedCharField, EncryptedIntegerField, EncryptedTextField
from partial_index import PQ, PartialIndex
from simple_history.models import HistoricalRecords

from care.facility.models import (
    DISEASE_CHOICES,
    BaseManager,
    District,
    FacilityBaseModel,
    LocalBody,
    PatientBaseModel,
    State,
    reverse_choices,
)
from care.facility.models.mixins.permissions.patient import PatientPermissionMixin
from care.facility.models.patient_base import BLOOD_GROUP_CHOICES, DISEASE_STATUS_CHOICES
from care.users.models import GENDER_CHOICES, REVERSE_GENDER_CHOICES, User, phone_number_regex
from care.utils.models.jsonfield import JSONField
from care.facility.models.mixins.permissions.facility import FacilityRelatedPermissionMixin


class ShiftingRequest(FacilityBaseModel):

    STATUS_CHOICES = (
        (10, "PENDING"),
        (20, "APPROVED"),
        (30, "REJECTED"),
        (40, "DESTINATION APPROVED"),
        (50, "DESTINATION REJECTED"),
        (60, "AWAITING TRANSPORTATION"),
        (70, "TRANSFER IN PROGRESS"),
        (80, "COMPLETED"),
    )

    orgin_facility = models.ForeignKey("Facility", on_delete=models.PROTECT, related_name="requesting_facility")
    shifting_approving_facility = models.ForeignKey(
        "Facility", on_delete=models.SET_NULL, null=True, related_name="shifting_approving_facility"
    )
    assigned_facility = models.ForeignKey(
        "Facility", on_delete=models.SET_NULL, null=True, related_name="assigned_facility"
    )
    emergency = models.BooleanField(default=False)
    is_up_shift = models.BooleanField(default=False)  # False for Down , True for UP
    reason = models.TextField(default="", blank=True)
    vehicle_preference = models.TextField(default="", blank=True)
    comments = models.TextField(default="", blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=10, null=False, blank=False)
