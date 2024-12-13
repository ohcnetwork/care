from django.db import models

from care.facility.models.base import FacilityBaseModel
from care.facility.models.patient import PatientRegistration
from care.facility.models.schedule import (
    Availability,
    SchedulableResource,
    ScheduleException,
    TokenBookingStatus,
)
from care.users.models import User


class TokenSlot(FacilityBaseModel):
    resource = models.ForeignKey(
        SchedulableResource, on_delete=models.CASCADE, null=False, blank=False
    )
    availability = models.ForeignKey(
        Availability, on_delete=models.CASCADE, null=True, blank=True
    )
    availability_exception = models.ForeignKey(
        ScheduleException, on_delete=models.CASCADE, null=True, blank=True
    )
    start_datetime = models.DateTimeField(null=False, blank=False)
    end_datetime = models.DateTimeField(null=False, blank=False)
    tokens_count = models.IntegerField(null=False, blank=False, default=0)
    tokens_remaining = models.IntegerField(null=False, blank=False, default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(tokens_remaining__gte=0),
                name="tokens_remaining_non_negative",
            ),
            models.UniqueConstraint(
                fields=["resource", "start_datetime"],
                name="unique_resource_slot",
            ),
        ]


class TokenBooking(FacilityBaseModel):
    token_slot = models.ForeignKey(
        TokenSlot, on_delete=models.CASCADE, null=False, blank=False
    )
    patient = models.ForeignKey(
        PatientRegistration, on_delete=models.CASCADE, null=False, blank=False
    )

    booked_on = models.DateTimeField(auto_now_add=True)
    booked_by = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, blank=False
    )
    status = models.CharField(
        max_length=20,
        choices=TokenBookingStatus.choices,
        default=TokenBookingStatus.REQUESTED,
    )
    reason_for_visit = models.TextField(null=True, blank=True)

    @staticmethod
    def has_read_permission(request):
        return True

    @staticmethod
    def has_write_permission(request):
        return True
