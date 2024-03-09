from django.db import models
from django.utils.translation import gettext_lazy as _

from care.facility.models import (
    FacilityTypes,
    FacilityBaseModel,
    pretty_boolean,
)
from care.users.models import User
from care.utils.models.validators import mobile_or_landline_number_validator


#
# SHIFTING_STATUS_CHOICES = (
#     (10, "PENDING"),
#     (15, "ON HOLD"),
#     (20, "APPROVED"),
#     (30, "REJECTED"),
#     (40, "DESTINATION APPROVED"),
#     (50, "DESTINATION REJECTED"),
#     (55, "TRANSPORTATION TO BE ARRANGED"),
#     (60, "PATIENT TO BE PICKED UP"),
#     (70, "TRANSFER IN PROGRESS"),
#     (80, "COMPLETED"),
#     (90, "PATIENT EXPIRED"),
#     (100, "CANCELLED"),
# )

# VEHICLE_CHOICES = [
#     (10, "D Level Ambulance"),
#     (20, "All double chambered Ambulance with EMT"),
#     (30, "Ambulance without EMT"),
#     (40, "Car"),
#     (50, "Auto-rickshaw"),
# ]
#
# BREATHLESSNESS_CHOICES = [
#     (10, "NOT SPECIFIED"),
#     (15, "NOT BREATHLESS"),
#     (20, "MILD"),
#     (30, "MODERATE"),
#     (40, "SEVERE"),
# ]

class ShiftingStatusChoices(models.IntegerChoices):
    PENDING = 10, _("Pending")
    ON_HOLD = 15, _("On Hold")
    APPROVED = 20, _("Approved")
    REJECTED = 30, _("Rejected")
    DESTINATION_APPROVED = 40, _("Destination Approved")
    DESTINATION_REJECTED = 50, _("Destination Rejected")
    TRANSPORTATION_TO_BE_ARRANGED = 55, _("Transportation to be Arranged")
    PATIENT_TO_BE_PICKED_UP = 60, _("Patient to be Picked Up")
    TRANSFER_IN_PROGRESS = 70, _("Transfer in Progress")
    COMPLETED = 80, _("Completed")
    PATIENT_EXPIRED = 90, _("Patient Expired")
    CANCELLED = 100, _("Cancelled")


class VehicleTypeChoices(models.IntegerChoices):
    D_LEVEL_AMBULANCE = 10, _("D Level Ambulance")
    DOUBLE_CHAMBERED_AMBULANCE_WITH_EMT = 20, _("All double chambered Ambulance with EMT")
    AMBULANCE_WITHOUT_EMT = 30, _("Ambulance without EMT")
    CAR = 40, _("Car")
    AUTO_RICKSHAW = 50, _("Auto-rickshaw")


class BreathlessnessLevelChoices(models.IntegerChoices):
    NOT_SPECIFIED = 10, _("Not Specified")
    NOT_BREATHLESS = 15, _("Not Breathless")
    MILD = 20, _("Mild")
    MODERATE = 30, _("Moderate")
    SEVERE = 40, _("Severe")


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
        choices=FacilityTypes, default=None, null=True, blank=True
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
        choices=VehicleTypeChoices.choices, default=None, null=True, blank=True
    )
    comments = models.TextField(default="", blank=True)
    refering_facility_contact_name = models.TextField(default="", blank=True)
    refering_facility_contact_number = models.CharField(
        max_length=14,
        validators=[mobile_or_landline_number_validator],
        default="",
        blank=True,
    )
    is_kasp = models.BooleanField(default=False)
    status = models.IntegerField(
        choices=ShiftingStatusChoices.choices, default=ShiftingStatusChoices.PENDING, null=False, blank=False
    )

    breathlessness_level = models.IntegerField(
        choices=BreathlessnessLevelChoices.choices, default=BreathlessnessLevelChoices.NOT_SPECIFIED, null=True, blank=True
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
        max_length=14,
        validators=[mobile_or_landline_number_validator],
        default="",
        blank=True,
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
        "status": (lambda x: ShiftingStatusChoices(x) if x in ShiftingStatusChoices.values else "-"),
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
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]
        )

    @staticmethod
    def has_read_permission(request):
        return request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]

    def has_object_read_permission(self, request):
        return request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]

    def has_object_write_permission(self, request):
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]
        )

    def has_object_transfer_permission(self, request):
        return self.has_object_write_permission(request)

    def has_object_update_permission(self, request):
        return self.has_object_write_permission(request)


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

    @staticmethod
    def has_write_permission(request):
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]
        )

    @staticmethod
    def has_read_permission(request):
        return request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]

    def has_object_read_permission(self, request):
        return request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]

    def has_object_write_permission(self, request):
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]
        )

    def has_object_update_permission(self, request):
        return self.has_object_write_permission(request)
