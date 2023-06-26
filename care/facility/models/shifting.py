from django.db import models

from care.facility.models import (
    FACILITY_TYPES,
    READ_ONLY_USER_TYPES,
    FacilityBaseModel,
    pretty_boolean,
    reverse_choices,
)
from care.users.models import User, phone_number_regex

SHIFTING_STATUS_CHOICES = (
    (10, "PENDING"),
    (15, "ON HOLD"),
    (20, "APPROVED"),
    (30, "REJECTED"),
    (40, "DESTINATION APPROVED"),
    (50, "DESTINATION REJECTED"),
    (55, "TRANSPORTATION TO BE ARRANGED"),
    (60, "PATIENT TO BE PICKED UP"),
    (70, "TRANSFER IN PROGRESS"),
    (80, "COMPLETED"),
    (90, "PATIENT EXPIRED"),
    (100, "CANCELLED"),
)

VEHICLE_CHOICES = [
    (10, "D Level Ambulance"),
    (20, "All double chambered Ambulance with EMT"),
    (30, "Ambulance without EMT"),
    (40, "Car"),
    (50, "Auto-rickshaw"),
]

BREATHLESSNESS_CHOICES = [
    (10, "NOT SPECIFIED"),
    (15, "NOT BREATHLESS"),
    (20, "MILD"),
    (30, "MODERATE"),
    (40, "SEVERE"),
]

REVERSE_SHIFTING_STATUS_CHOICES = reverse_choices(SHIFTING_STATUS_CHOICES)


class ShiftingRequest(FacilityBaseModel):
    origin_facility = models.ForeignKey(
        "Facility",
        on_delete=models.PROTECT,
        related_name="requesting_facility",
    )
    shifting_approving_facility = models.ForeignKey(
        "Facility",
        on_delete=models.SET_NULL,
        null=True,
        related_name="shifting_approving_facility",
    )
    assigned_facility_type = models.IntegerField(
        choices=FACILITY_TYPES, default=None, null=True, blank=True
    )
    assigned_facility = models.ForeignKey(
        "Facility",
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_facility",
    )
    assigned_facility_external = models.TextField(default="", null=True, blank=True)
    patient = models.ForeignKey(
        "PatientRegistration", on_delete=models.CASCADE, related_name="patient"
    )
    emergency = models.BooleanField(default=False)
    is_up_shift = models.BooleanField(default=False)  # False for Down , True for UP
    reason = models.TextField(default="", blank=True)
    vehicle_preference = models.TextField(default="", blank=True)
    preferred_vehicle_choice = models.IntegerField(
        choices=VEHICLE_CHOICES, default=None, null=True, blank=True
    )
    comments = models.TextField(default="", blank=True)
    refering_facility_contact_name = models.TextField(default="", blank=True)
    refering_facility_contact_number = models.CharField(
        max_length=14, validators=[phone_number_regex], default="", blank=True
    )
    is_kasp = models.BooleanField(default=False)
    status = models.IntegerField(
        choices=SHIFTING_STATUS_CHOICES, default=10, null=False, blank=False
    )

    breathlessness_level = models.IntegerField(
        choices=BREATHLESSNESS_CHOICES, default=10, null=True, blank=True
    )

    is_assigned_to_user = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="shifting_assigned_to",
    )
    ambulance_driver_name = models.TextField(default="", blank=True)
    ambulance_phone_number = models.CharField(
        max_length=14, validators=[phone_number_regex], default="", blank=True
    )
    ambulance_number = models.TextField(default="", blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="shifting_created_by",
    )
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="shifting_last_edited_by",
    )

    CSV_MAPPING = {
        "created_date": "Created Date",
        "modified_date": "Modified Date",
        "patient__name": "Patient Name",
        "patient__phone_number": "Patient Phone Number",
        "patient__age": "Patient Age",
        "patient__is_antenatal": "Patient is Antenatal",
        "origin_facility__name": "From Facility",
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
        "patient__is_antenatal": pretty_boolean,
    }

    class Meta:
        indexes = [
            models.Index(fields=["status", "deleted"]),
        ]

    @staticmethod
    def has_write_permission(request):
        if request.user.user_type in READ_ONLY_USER_TYPES:
            return False
        return True

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return True

    def has_object_write_permission(self, request):
        if request.user.user_type in READ_ONLY_USER_TYPES:
            return False
        return True

    def has_object_transfer_permission(self, request):
        return True

    def has_object_update_permission(self, request):
        if request.user.user_type in READ_ONLY_USER_TYPES:
            return False
        return True


class ShiftingRequestComment(FacilityBaseModel):
    request = models.ForeignKey(
        ShiftingRequest, on_delete=models.PROTECT, null=False, blank=False
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    comment = models.TextField(default="", blank=True)
