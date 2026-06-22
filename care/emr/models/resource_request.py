from django.db import models

from care.emr.models import EMRBaseModel, Patient
from care.users.models import User
from care.utils.models.validators import mobile_or_landline_number_validator


class ResourceRequest(EMRBaseModel):
    origin_facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.PROTECT,
        related_name="resource_requesting_facilities",
    )
    approving_facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_approving_facilities",
    )
    assigned_facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_assigned_facilities",
    )
    emergency = models.BooleanField(default=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    reason = models.TextField(default="")
    referring_facility_contact_name = models.TextField(default="", blank=True)
    referring_facility_contact_number = models.CharField(
        max_length=14,
        validators=[mobile_or_landline_number_validator],
        default="",
        blank=True,
    )
    status = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    priority = models.IntegerField(default=None, null=True, blank=True)
    is_assigned_to_user = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_request_assigned",
    )

    related_patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        blank=True,
    )

    extensions = models.JSONField(default=dict)


class ResourceRequestComment(EMRBaseModel):
    request = models.ForeignKey(
        ResourceRequest, on_delete=models.PROTECT, null=False, blank=False
    )
    comment = models.TextField(default="")
