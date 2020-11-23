import enum

from django.db import models

from care.facility.models import FacilityBaseModel
from care.users.models import User
from django.contrib.postgres.fields import JSONField


class Notification(FacilityBaseModel):
    class EventType(enum.Enum):
        SYSTEM_GENERATED = 50
        CUSTOM_MESSAGE = 100

    EventTypeChoices = [(e.value, e.name) for e in EventType]

    class Event(enum.Enum):
        MESSAGE = 0
        PATIENT_CREATED = 20
        PATIENT_UPDATED = 30
        PATIENT_DELETED = 40

    EventChoices = [(e.value, e.name) for e in Event]

    intended_for = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_intended_for",
    )
    caused_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_caused_by",
    )
    read_at = models.DateTimeField(null=True, blank=True)
    event_type = models.IntegerField(
        choices=EventTypeChoices, default=EventType.SYSTEM_GENERATED.value
    )
    event = models.IntegerField(choices=EventChoices, default=Event.MESSAGE.value)
    message = models.TextField(max_length=2000, null=True, default=None)
    caused_objects = JSONField(null=True, blank=True, default=dict)
