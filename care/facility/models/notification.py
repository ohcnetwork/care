from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _

from care.facility.models import FacilityBaseModel
from care.users.models import User


class Notification(FacilityBaseModel):
    # class EventType(enum.Enum):
    #     SYSTEM_GENERATED = 50
    #     CUSTOM_MESSAGE = 100
    #
    # EventTypeChoices = [(e.value, e.name) for e in EventType]
    #
    # class Medium(enum.Enum):
    #     SYSTEM = 0
    #     SMS = 100
    #     WHATSAPP = 200
    #
    # MediumChoices = [(e.value, e.name) for e in Medium]
    class EventTypeChoices(models.IntegerChoices):
        SYSTEM_GENERATED = 50, _("System Generated")
        CUSTOM_MESSAGE = 100, _("Custom Message")

    class MediumChoices(models.IntegerChoices):
        SYSTEM = 0, _("System")
        SMS = 100, _("SMS")
        WHATSAPP = 200, _("WhatsApp")

    # class Event(enum.Enum):
    #     MESSAGE = 0
    #     PATIENT_CREATED = 20
    #     PATIENT_UPDATED = 30
    #     PATIENT_DELETED = 40
    #     PATIENT_CONSULTATION_CREATED = 50
    #     PATIENT_CONSULTATION_UPDATED = 60
    #     PATIENT_CONSULTATION_DELETED = 70
    #     INVESTIGATION_SESSION_CREATED = 80
    #     INVESTIGATION_UPDATED = 90
    #     PATIENT_FILE_UPLOAD_CREATED = 100
    #     CONSULTATION_FILE_UPLOAD_CREATED = 110
    #     PATIENT_CONSULTATION_UPDATE_CREATED = 120
    #     PATIENT_CONSULTATION_UPDATE_UPDATED = 130
    #     PATIENT_CONSULTATION_ASSIGNMENT = 140
    #     SHIFTING_UPDATED = 200
    #     PATIENT_NOTE_ADDED = 210
    #     PUSH_MESSAGE = 220
    #
    # EventChoices = [(e.value, e.name) for e in Event]

    class EventChoices(models.IntegerChoices):
        MESSAGE = 0, _("Message")
        PATIENT_CREATED = 20, _("Patient Created")
        PATIENT_UPDATED = 30, _("Patient Updated")
        PATIENT_DELETED = 40, _("Patient Deleted")
        PATIENT_CONSULTATION_CREATED = 50, _("Patient Consultation Created")
        PATIENT_CONSULTATION_UPDATED = 60, _("Patient Consultation Updated")
        PATIENT_CONSULTATION_DELETED = 70, _("Patient Consultation Deleted")
        INVESTIGATION_SESSION_CREATED = 80, _("Investigation Session Created")
        INVESTIGATION_UPDATED = 90, _("Investigation Updated")
        PATIENT_FILE_UPLOAD_CREATED = 100, _("Patient File Upload Created")
        CONSULTATION_FILE_UPLOAD_CREATED = 110, _("Consultation File Upload Created")
        PATIENT_CONSULTATION_UPDATE_CREATED = 120, _("Patient Consultation Update Created")
        PATIENT_CONSULTATION_UPDATE_UPDATED = 130, _("Patient Consultation Update Updated")
        PATIENT_CONSULTATION_ASSIGNMENT = 140, _("Patient Consultation Assignment")
        SHIFTING_UPDATED = 200, _("Shifting Updated")
        PATIENT_NOTE_ADDED = 210, _("Patient Note Added")
        PUSH_MESSAGE = 220, _("Push Message")

    intended_for = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_intended_for",
    )
    medium_sent = models.IntegerField(
        choices=MediumChoices.choices, default=MediumChoices.SYSTEM
    )
    caused_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_caused_by",
    )
    read_at = models.DateTimeField(null=True, blank=True)
    event_type = models.IntegerField(
        choices=EventTypeChoices.choices, default=EventTypeChoices.SYSTEM_GENERATED
    )
    event = models.IntegerField(choices=EventChoices.choices, default=EventChoices.MESSAGE)
    message = models.TextField(max_length=2000, null=True, default=None)
    caused_objects = JSONField(null=True, blank=True, default=dict)
