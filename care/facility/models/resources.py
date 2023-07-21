from django.db import models

from care.facility.models import (
    READ_ONLY_USER_TYPES,
    FacilityBaseModel,
    pretty_boolean,
    reverse_choices,
)
from care.users.models import User, phone_number_regex

RESOURCE_STATUS_CHOICES = (
    (10, "PENDING"),
    (15, "ON HOLD"),
    (20, "APPROVED"),
    (30, "REJECTED"),
    (55, "TRANSPORTATION TO BE ARRANGED"),
    (70, "TRANSFER IN PROGRESS"),
    (80, "COMPLETED"),
)

RESOURCE_CATEGORY_CHOICES = (
    (100, "OXYGEN"),
    (200, "SUPPLIES"),
)

RESOURCE_SUB_CATEGORY_CHOICES = (
    (110, "LIQUID OXYGEN"),
    (120, "B TYPE OXYGEN CYLINDER"),
    (130, "C TYPE OXYGEN CYLINDER"),
    (140, "JUMBO D TYPE OXYGEN CYLINDER"),
    (1000, "UNSPECIFIED"),
)

REVERSE_CATEGORY = reverse_choices(RESOURCE_CATEGORY_CHOICES)
REVERSE_SUB_CATEGORY = reverse_choices(RESOURCE_SUB_CATEGORY_CHOICES)


class ResourceRequest(FacilityBaseModel):
    origin_facility = models.ForeignKey(
        "Facility",
        on_delete=models.PROTECT,
        related_name="resource_requesting_facility",
    )
    approving_facility = models.ForeignKey(
        "Facility",
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_approving_facility",
    )
    assigned_facility = models.ForeignKey(
        "Facility",
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_assigned_facility",
    )
    emergency = models.BooleanField(default=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    reason = models.TextField(default="", blank=True)
    refering_facility_contact_name = models.TextField(default="", blank=True)
    refering_facility_contact_number = models.CharField(
        max_length=14, validators=[phone_number_regex], default="", blank=True
    )
    status = models.IntegerField(
        choices=RESOURCE_STATUS_CHOICES, default=10, null=False, blank=False
    )
    category = models.IntegerField(
        choices=RESOURCE_CATEGORY_CHOICES, default=100, null=False, blank=False
    )
    sub_category = models.IntegerField(
        choices=RESOURCE_SUB_CATEGORY_CHOICES, default=1000, null=False, blank=False
    )
    priority = models.IntegerField(default=None, null=True, blank=True)

    # Quantity
    requested_quantity = models.IntegerField(default=0)
    assigned_quantity = models.IntegerField(default=0)

    is_assigned_to_user = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_request_assigned_to",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_request_created_by",
    )
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_request_last_edited_by",
    )

    CSV_MAPPING = {
        "created_date": "Created Date",
        "modified_date": "Modified Date",
        "origin_facility__name": "From Facility",
        "assigned_facility__name": "Assigned Facility",
        "approving_facility__name": "Approving Facility",
        "status": "Current Status",
        "emergency": "Emergency Shift",
        "reason": "Reason for Shifting",
        "title": "Title",
        "category": "Category",
        "sub_category": "Sub Category",
        "priority": "Priority",
        "requested_quantity": "Requested Quantity",
        "assigned_quantity": "Assigned Quantity",
        "assigned_to__username": "Assigned User Username",
    }

    CSV_MAKE_PRETTY = {
        "category": (lambda x: REVERSE_CATEGORY.get(x, "-")),
        "sub_category": (lambda x: REVERSE_SUB_CATEGORY.get(x, "-")),
        "emergency": pretty_boolean,
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


class ResourceRequestComment(FacilityBaseModel):
    request = models.ForeignKey(
        ResourceRequest, on_delete=models.PROTECT, null=False, blank=False
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    comment = models.TextField(default="", blank=True)
