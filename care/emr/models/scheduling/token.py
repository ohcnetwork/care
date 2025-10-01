from django.db import models

from care.emr.models import EMRBaseModel


class TokenQueue(EMRBaseModel):
    """
    Represents a queue of token for a given resource for a given date
    """

    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    resource = models.ForeignKey("emr.SchedulableResource", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=True)
    date = models.DateField()
    system_generated = models.BooleanField(default=False)


class TokenSubQueue(EMRBaseModel):
    """
    Represents a sub queue for a given resource.
    This allows tokens to be placed in sub queue categories for easy splits.
    ex for vaccination, the user might get a token but there might be
    multiple rooms that gets assigned tokens each of these rooms will have a sub queue
    """

    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    resource = models.ForeignKey("emr.SchedulableResource", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    current_token = models.ForeignKey(
        "emr.Token", on_delete=models.CASCADE, null=True, blank=True
    )


class TokenCategory(EMRBaseModel):
    """
    Represents categories for tokens
    """

    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    resource_type = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    shorthand = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)
    default = models.BooleanField(default=False)


class Token(EMRBaseModel):
    """
    Represents a token given to a patient,
    A patient might have multiple tokens in a given queue
    """

    facility = models.ForeignKey("facility.Facility", on_delete=models.CASCADE)
    patient = models.ForeignKey(
        "emr.Patient", on_delete=models.CASCADE, null=True, blank=True
    )
    queue = models.ForeignKey(TokenQueue, on_delete=models.CASCADE)
    category = models.ForeignKey(TokenCategory, on_delete=models.CASCADE)
    sub_queue = models.ForeignKey(
        TokenSubQueue, on_delete=models.CASCADE, null=True, blank=True
    )
    number = models.IntegerField()
    status = models.CharField(max_length=255)
    is_next = models.BooleanField(default=False)
    note = models.TextField(null=True, blank=True)
    booking = models.ForeignKey(
        "emr.TokenBooking",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="booking_token",
    )
