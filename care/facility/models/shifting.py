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
    PatientRegistration,
    reverse_choices,
    pretty_boolean,
)
from care.facility.models.mixins.permissions.patient import PatientPermissionMixin
from care.facility.models.patient_base import BLOOD_GROUP_CHOICES, DISEASE_STATUS_CHOICES
from care.users.models import GENDER_CHOICES, REVERSE_GENDER_CHOICES, User, phone_number_regex
from care.utils.models.jsonfield import JSONField
from care.facility.models.mixins.permissions.facility import FacilityRelatedPermissionMixin


SHIFTING_STATUS_CHOICES = (
    (10, "PENDING"),
    (20, "APPROVED"),
    (30, "REJECTED"),
    (40, "DESTINATION APPROVED"),
    (50, "DESTINATION REJECTED"),
    (60, "AWAITING TRANSPORTATION"),
    (70, "TRANSFER IN PROGRESS"),
    (80, "COMPLETED"),
)

REVERSE_SHIFTING_STATUS_CHOICES = reverse_choices(SHIFTING_STATUS_CHOICES)


class ShiftingRequest(FacilityBaseModel):

    orgin_facility = models.ForeignKey("Facility", on_delete=models.PROTECT, related_name="requesting_facility")
    shifting_approving_facility = models.ForeignKey(
        "Facility", on_delete=models.SET_NULL, null=True, related_name="shifting_approving_facility"
    )
    assigned_facility = models.ForeignKey(
        "Facility", on_delete=models.SET_NULL, null=True, related_name="assigned_facility"
    )
    patient = models.ForeignKey("PatientRegistration", on_delete=models.CASCADE, related_name="patient")
    emergency = models.BooleanField(default=False)
    is_up_shift = models.BooleanField(default=False)  # False for Down , True for UP
    reason = models.TextField(default="", blank=True)
    vehicle_preference = models.TextField(default="", blank=True)
    comments = models.TextField(default="", blank=True)
    status = models.IntegerField(choices=SHIFTING_STATUS_CHOICES, default=10, null=False, blank=False)

    CSV_MAPPING = {
        "created_date": "Created Date",
        "modified_date": "Modified Date",
        "patient__name": "Patient Name",
        "patient__phone_number": "Patient Phone Number",
        "patient__age": "Patient Age",
        "orgin_facility__name": "From Facility",
        "assigned_facility__name": "To Facility",
        "shifting_approving_facility__name": "Approving Facility",
        "status": "Current Status",
        "is_up_shift": "Upshift",
        "emergency": "Emergency Shift",
        "vehicle_preference": "Vehicle Preference",
        "reason": "Reason for Shifting",
    }

    CSV_MAKE_PRETTY = {
        "status": (lambda x: REVERSE_SHIFTING_STATUS_CHOICES.get(x, "-")),
        "is_up_shift": pretty_boolean,
        "emergency": pretty_boolean,
    }

    @staticmethod
    def has_write_permission(request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False
        return True

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return True

    def has_object_update_permission(self, request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False
        return True
