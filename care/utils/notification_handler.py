from care.facility.models.patient_consultation import PatientConsultation
from care.facility.models.patient import PatientRegistration
from care.facility.models.notification import Notification
from care.facility.models.facility import Facility
from care.users.models import User

from care.facility.tasks.notification.generator import (
    generate_notifications_for_facility,
)


class NotificationCreationException(Exception):
    pass


class NotificationGenerator:

    generate_for_facility = False
    generate_for_user = False
    facility = None

    def __init__(
        self,
        event_type=Notification.EventType.SYSTEM_GENERATED,
        event=None,
        caused_by=None,
        caused_object=None,
        message=None,
        defer_notifications=False,
        facility=None,
        generate_for_facility=False,
    ):
        if not isinstance(event_type, Notification.EventType):
            raise NotificationCreationException("Event Type Invalid")
        if not isinstance(event, Notification.Event):
            raise NotificationCreationException("Event Invalid")
        if not isinstance(caused_by, User):
            raise NotificationCreationException(
                "edited_by must be an instance of a user"
            )
        if facility:
            if not isinstance(facility, Facility):
                raise NotificationCreationException(
                    "facility must be an instance of Facility"
                )
        self.event_type = event_type.value
        self.event = event.value
        self.caused_by = caused_by
        self.caused_object = caused_object
        self.caused_objects = {}
        self.generate_cause_objects()
        self.message = None
        if not message:
            self.generate_message()
        else:
            self.message = message
        self.facility = facility
        self.generate_for_facility = generate_for_facility
        self.defer_notifications = defer_notifications

    def generate_message(self):
        if isinstance(self.caused_object, PatientRegistration):
            if self.event == Notification.Event.PATIENT_CREATED.value:
                self.message = "Patient {} was created by {}".format(
                    self.caused_object.name, self.caused_by.get_full_name()
                )
            elif self.event == Notification.Event.PATIENT_UPDATED.value:
                self.message = "Patient {} was updated by {}".format(
                    self.caused_object.name, self.caused_by.get_full_name()
                )
            if self.event == Notification.Event.PATIENT_DELETED.value:
                self.message = "Patient {} was deleted by {}".format(
                    self.caused_object.name, self.caused_by.get_full_name()
                )
        if isinstance(self.caused_object, PatientConsultation):
            if self.event == Notification.Event.PATIENT_CONSULTATION_CREATED.value:
                self.message = "Consultation for Patient {} was created by {}".format(
                    self.caused_object.patient.name, self.caused_by.get_full_name()
                )
            elif self.event == Notification.Event.PATIENT_CONSULTATION_UPDATED.value:
                self.message = "Consultation for Patient {} was updated by {}".format(
                    self.caused_object.patient.name, self.caused_by.get_full_name()
                )
            if self.event == Notification.Event.PATIENT_CONSULTATION_DELETED.value:
                self.message = "Consultation for Patient {} was deleted by {}".format(
                    self.caused_object.patient.name, self.caused_by.get_full_name()
                )
        return True

    def generate_cause_objects(self):
        if isinstance(self.caused_object, PatientRegistration):
            self.caused_objects["patient"] = self.caused_object.external_id
            if self.caused_object.facility:
                self.caused_objects[
                    "facility"
                ] = self.caused_object.facility.external_id
        if isinstance(self.caused_object, PatientConsultation):
            self.caused_objects["consultation"] = self.caused_object.external_id
            self.caused_objects["patient"] = self.caused_object.patient.external_id
            if self.caused_object.patient.facility:
                self.caused_objects[
                    "facility"
                ] = self.caused_object.patient.facility.external_id

        return True

    def generate(self):
        data = {
            "caused_by_id": self.caused_by.id,
            "event": self.event,
            "event_type": self.event_type,
            "caused_objects": self.caused_objects,
            "message": self.message,
        }
        generate_notifications_for_facility.delay(
            self.facility.id, data, self.defer_notifications
        )

