import enum

from django.db import models
from django.db.models import JSONField

from care.facility.models import FacilityBaseModel
from care.users.models import User


class Notification(FacilityBaseModel):
    class EventType(enum.Enum):
        SYSTEM_GENERATED = 50
        CUSTOM_MESSAGE = 100

    EventTypeChoices = [(e.value, e.name) for e in EventType]

    class Medium(enum.Enum):
        SYSTEM = 0
        SMS = 100
        WHATSAPP = 200

    MediumChoices = [(e.value, e.name) for e in Medium]

    class Event(enum.Enum):
        MESSAGE = 0
        PATIENT_CREATED = 20
        PATIENT_UPDATED = 30
        PATIENT_DELETED = 40
        PATIENT_CONSULTATION_CREATED = 50
        PATIENT_CONSULTATION_UPDATED = 60
        PATIENT_CONSULTATION_DELETED = 70
        INVESTIGATION_SESSION_CREATED = 80
        INVESTIGATION_UPDATED = 90
        PATIENT_FILE_UPLOAD_CREATED = 100
        CONSULTATION_FILE_UPLOAD_CREATED = 110
        PATIENT_CONSULTATION_UPDATE_CREATED = 120
        PATIENT_CONSULTATION_UPDATE_UPDATED = 130
        PATIENT_CONSULTATION_ASSIGNMENT = 140
        SHIFTING_UPDATED = 200
        PATIENT_NOTE_ADDED = 210
        PUSH_MESSAGE = 220
        PATIENT_PRESCRIPTION_CREATED = 230
        PATIENT_PRESCRIPTION_UPDATED = 240

    EventChoices = [(e.value, e.name) for e in Event]

    intended_for = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_intended_for",
    )
    medium_sent = models.IntegerField(
        choices=MediumChoices, default=Medium.SYSTEM.value
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
