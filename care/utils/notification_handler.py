from care.facility.models.shifting import ShiftingRequest
from care.facility.models.patient_consultation import PatientConsultation, DailyRound
from care.facility.models.patient import PatientRegistration
from care.facility.models.notification import Notification
from care.facility.models.facility import Facility
from care.facility.models.patient_investigation import InvestigationValue, InvestigationSession
from care.users.models import User

from care.facility.tasks.notification.generator import generate_notifications_for_facility, generate_sms_for_user


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
        extra_users=None,
        extra_data=None,
        generate_sms=False,
    ):
        if not isinstance(event_type, Notification.EventType):
            raise NotificationCreationException("Event Type Invalid")
        if not isinstance(event, Notification.Event):
            raise NotificationCreationException("Event Invalid")
        if not isinstance(caused_by, User):
            raise NotificationCreationException("edited_by must be an instance of a user")
        if facility:
            if not isinstance(facility, Facility):
                raise NotificationCreationException("facility must be an instance of Facility")
        self.event_type = event_type.value
        self.event = event.value
        self.caused_by = caused_by
        self.caused_object = caused_object
        self.caused_objects = {}
        self.extra_data = extra_data
        self.generate_cause_objects()
        self.message = None
        self.extra_users = []
        if extra_users:
            self.extra_users = extra_users
        if not message:
            self.generate_message()
        else:
            self.message = message
        self.facility = facility
        self.generate_for_facility = generate_for_facility
        self.defer_notifications = defer_notifications
        self.generate_extra_users()
        self.generate_sms = generate_sms

    def generate_extra_users(self):
        if isinstance(self.caused_object, PatientConsultation):
            if self.caused_object.assigned_to:
                self.extra_users.append(self.caused_object.assigned_to.id)
        if isinstance(self.caused_object, PatientRegistration):
            if self.caused_object.last_consultation:
                if self.caused_object.last_consultation.assigned_to:
                    self.extra_users.append(self.caused_object.last_consultation.assigned_to.id)
        if isinstance(self.caused_object, InvestigationSession):
            if self.extra_data["consultation"].assigned_to:
                self.extra_users.append(self.extra_data["consultation"].assigned_to.id)
        if isinstance(self.caused_object, InvestigationValue):
            if self.caused_object.consultation.assigned_to:
                self.extra_users.append(self.caused_object.consultation.assigned_to.id)
        if isinstance(self.caused_object, DailyRound):
            if self.caused_object.consultation.assigned_to:
                self.extra_users.append(self.caused_object.consultation.assigned_to.id)

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
        if isinstance(self.caused_object, InvestigationSession):
            if self.event == Notification.Event.INVESTIGATION_SESSION_CREATED.value:
                self.message = "Investigation Session for Patient {} was created by {}".format(
                    self.extra_data["consultation"].patient.name, self.caused_by.get_full_name()
                )
        if isinstance(self.caused_object, InvestigationValue):
            if self.event == Notification.Event.INVESTIGATION_UPDATED.value:
                self.message = "Investigation Value for {} for Patient {} was updated by {}".format(
                    self.caused_object.investigation.name,
                    self.caused_object.consultation.patient.name,
                    self.caused_by.get_full_name(),
                )
        if isinstance(self.caused_object, DailyRound):
            if self.event == Notification.Event.PATIENT_CONSULTATION_UPDATE_CREATED.value:
                self.message = "Consultation for Patient {}  at facility {} was created by {}".format(
                    self.caused_object.consultation.patient.name,
                    self.caused_object.consultation.facility.name,
                    self.caused_by.get_full_name(),
                )
            elif self.event == Notification.Event.PATIENT_CONSULTATION_UPDATE_UPDATED.value:
                self.message = "Consultation for Patient {}  at facility {} was updated by {}".format(
                    self.caused_object.consultation.patient.name,
                    self.caused_object.consultation.facility.name,
                    self.caused_by.get_full_name(),
                )
        if isinstance(self.caused_object, ShiftingRequest):
            if self.event == Notification.Event.SHIFTING_UPDATED.value:
                if self.caused_object.assigned_to:
                    self.message = "Your Shifting Request to {} has been approved , Your Assigned Contact is {} available at {}".format(
                        self.caused_object.assigned_facility.name,
                        self.caused_object.assigned_to.get_full_name(),
                        self.caused_object.assigned_to.phone_number,
                    )
                else:
                    self.message = "Your Shifting Request to {} has been approved in Care. Please contact {} for any queries".format(
                        self.caused_object.assigned_facility.name,
                        self.caused_object.shifting_approving_facility.phone_number,
                    )
        return True

    def generate_cause_objects(self):
        if isinstance(self.caused_object, PatientRegistration):
            self.caused_objects["patient"] = self.caused_object.external_id
            if self.caused_object.facility:
                self.caused_objects["facility"] = self.caused_object.facility.external_id
        if isinstance(self.caused_object, PatientConsultation):
            self.caused_objects["consultation"] = self.caused_object.external_id
            self.caused_objects["patient"] = self.caused_object.patient.external_id
            if self.caused_object.patient.facility:
                self.caused_objects["facility"] = self.caused_object.patient.facility.external_id
        if isinstance(self.caused_object, InvestigationSession):
            self.caused_objects["consultation"] = self.extra_data["consultation"].external_id
            self.caused_objects["patient"] = self.extra_data["consultation"].patient.external_id
            if self.extra_data["consultation"].patient.facility:
                self.caused_objects["facility"] = self.extra_data["consultation"].patient.facility.external_id
            self.caused_objects["session"] = self.caused_object.external_id
        if isinstance(self.caused_object, InvestigationValue):
            self.caused_objects["consultation"] = self.caused_object.consultation.external_id
            self.caused_objects["patient"] = self.caused_object.consultation.patient.external_id
            if self.caused_object.consultation.patient.facility:
                self.caused_objects["facility"] = self.caused_object.consultation.patient.facility.external_id
            self.caused_objects["session"] = self.caused_object.session.external_id
            self.caused_objects["investigation"] = self.caused_object.investigation.external_id
        if isinstance(self.caused_object, DailyRound):
            self.caused_objects["consultation"] = self.caused_object.consultation.external_id
            self.caused_objects["patient"] = self.caused_object.consultation.patient.external_id
            self.caused_objects["daily_round"] = self.caused_object.id
            if self.caused_object.consultation.patient.facility:
                self.caused_objects["facility"] = self.caused_object.consultation.facility.external_id

        return True

    def generate(self):
        if self.generate_sms:
            if isinstance(self.caused_object, ShiftingRequest):
                generate_sms_for_user(
                    [
                        self.caused_object.refering_facility_contact_number,
                        self.caused_object.patient.phone_number,
                        self.caused_object.patient.emergency_phone_number,
                    ],
                    self.message,
                )
        else:
            data = {
                "caused_by_id": self.caused_by.id,
                "event": self.event,
                "event_type": self.event_type,
                "caused_objects": self.caused_objects,
                "message": self.message,
                "extra_users": self.extra_users,
            }
            generate_notifications_for_facility.delay(self.facility.id, data, self.defer_notifications)

