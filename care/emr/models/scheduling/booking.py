from django.db import models

from care.emr.models import EMRBaseModel
from care.emr.models.scheduling.schedule import Availability, SchedulableUserResource
from care.users.models import User


class TokenSlot(EMRBaseModel):
    resource = models.ForeignKey(
        SchedulableUserResource, on_delete=models.CASCADE, null=False, blank=False
    )
    availability = models.ForeignKey(
        Availability, on_delete=models.CASCADE, null=True, blank=True
    )
    start_datetime = models.DateTimeField(null=False, blank=False)
    end_datetime = models.DateTimeField(null=False, blank=False)
    allocated = models.IntegerField(null=False, blank=False, default=0)
    # TODO propogate facility to this level or at the booking level to avoid joins


class TokenBooking(EMRBaseModel):
    token_slot = models.ForeignKey(
        TokenSlot, on_delete=models.PROTECT, null=False, blank=False
    )
    patient = models.ForeignKey(
        "emr.Patient",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    booked_on = models.DateTimeField(auto_now_add=True)
    booked_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField()
    reason_for_visit = models.TextField(null=True, blank=True)
