import json

import celery
from django.apps import apps
from django.conf import settings
from pywebpush import WebPushException, webpush

from care.facility.models.facility import Facility, FacilityUser
from care.facility.models.notification import Notification
from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_consultation import DailyRound, PatientConsultation
from care.facility.models.patient_investigation import InvestigationSession, InvestigationValue
from care.facility.models.shifting import ShiftingRequest
from care.users.models import User
from care.utils.sms.sendSMS import sendSMS
from care.utils.whatsapp.send_mesage import sendWhatsappMessage


class NotificationCreationException(Exception):
    pass


@celery.task()
def notification_task_generator(**kwargs):
    NotificationGenerator(**kwargs).generate()


def get_model_class(model_name):
    if model_name == "User":
        return apps.get_model("users.{}".format(model_name))
    return apps.get_model("facility.{}".format(model_name))


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
        caused_object_pk=None,
        message=None,
        defer_notifications=False,
        facility=None,
        generate_for_facility=False,
        extra_users=None,
        extra_data=None,
        notification_mediums=False,
        worker_initated=False,
    ):

        if not worker_initated:
            if not isinstance(event_type, Notification.EventType):
                raise NotificationCreationException("Event Type Invalid")
            if not isinstance(event, Notification.Event):
                raise NotificationCreationException("Event Invalid")
            if not isinstance(caused_by, User):
                raise NotificationCreationException("edited_by must be an instance of a user")
            if facility:
                if not isinstance(facility, Facility):
                    raise NotificationCreationException("facility must be an instance of Facility")
            mediums = []
            if notification_mediums:
                for medium in notification_mediums:
                    if not isinstance(medium, Notification.Medium):
                        raise NotificationCreationException("Medium Type Invalid")
                    mediums.append(medium.value)
            data = {
                "event_type": event_type.value,
                "event": event.value,
                "caused_by": caused_by.id,
                "caused_object": caused_object.__class__.__name__,
                "caused_object_pk": caused_object.id,
                "message": message,
                "defer_notifications": defer_notifications,
                "facility": facility.id,
                "generate_for_facility": generate_for_facility,
                "extra_users": extra_users,
                "extra_data": self.serialize_extra_data(extra_data),
                "notification_mediums": mediums,
                "worker_initated": True,
            }
            notification_task_generator.apply_async(kwargs=data, countdown=2)
            self.worker_initiated = False
            return
        self.worker_initiated = True
        Model = get_model_class(caused_object)
        caused_object = Model.objects.get(id=caused_object_pk)
        caused_by = User.objects.get(id=caused_by)
        facility = Facility.objects.get(id=facility)
        self.notification_mediums = notification_mediums
        if not notification_mediums:
            self.notification_mediums = self._get_default_medium()
        self.event_type = event_type
        self.event = event
        self.caused_by = caused_by
        self.caused_object = caused_object
        self.caused_objects = {}
        self.extra_data = self.deserialize_extra_data(extra_data)
        self.generate_cause_objects()
        self.extra_users = []
        self.message = message
        self.facility = facility
        self.generate_for_facility = generate_for_facility
        self.defer_notifications = defer_notifications
        self.generate_extra_users()

    def serialize_extra_data(self, extra_data):
        if not extra_data:
            return None
        for key in extra_data:
            extra_data[key] = {"model_name": extra_data[key].__class__.__name__, "model_id": extra_data[key].id}
        return extra_data

    def deserialize_extra_data(self, extra_data):
        if not extra_data:
            return None
        for key in extra_data:
            extra_data[key] = apps.get_model("facility.{}".format(extra_data[key]["model_name"])).objects.get(
                id=extra_data[key]["model_id"]
            )
        return extra_data

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

    def generate_system_message(self):
        message = ""
        if isinstance(self.caused_object, PatientRegistration):
            if self.event == Notification.Event.PATIENT_CREATED.value:
                message = "Patient {} was created by {}".format(
                    self.caused_object.name, self.caused_by.get_full_name()
                )
            elif self.event == Notification.Event.PATIENT_UPDATED.value:
                message = "Patient {} was updated by {}".format(
                    self.caused_object.name, self.caused_by.get_full_name()
                )
            if self.event == Notification.Event.PATIENT_DELETED.value:
                message = "Patient {} was deleted by {}".format(
                    self.caused_object.name, self.caused_by.get_full_name()
                )
        elif isinstance(self.caused_object, PatientConsultation):
            if self.event == Notification.Event.PATIENT_CONSULTATION_CREATED.value:
                message = "Consultation for Patient {} was created by {}".format(
                    self.caused_object.patient.name, self.caused_by.get_full_name()
                )
            elif self.event == Notification.Event.PATIENT_CONSULTATION_UPDATED.value:
                message = "Consultation for Patient {} was updated by {}".format(
                    self.caused_object.patient.name, self.caused_by.get_full_name()
                )
            if self.event == Notification.Event.PATIENT_CONSULTATION_DELETED.value:
                message = "Consultation for Patient {} was deleted by {}".format(
                    self.caused_object.patient.name, self.caused_by.get_full_name()
                )
        elif isinstance(self.caused_object, InvestigationSession):
            if self.event == Notification.Event.INVESTIGATION_SESSION_CREATED.value:
                message = "Investigation Session for Patient {} was created by {}".format(
                    self.extra_data["consultation"].patient.name, self.caused_by.get_full_name()
                )
        elif isinstance(self.caused_object, InvestigationValue):
            if self.event == Notification.Event.INVESTIGATION_UPDATED.value:
                message = "Investigation Value for {} for Patient {} was updated by {}".format(
                    self.caused_object.investigation.name,
                    self.caused_object.consultation.patient.name,
                    self.caused_by.get_full_name(),
                )
        elif isinstance(self.caused_object, DailyRound):
            if self.event == Notification.Event.PATIENT_CONSULTATION_UPDATE_CREATED.value:
                message = "Consultation for Patient {}  at facility {} was created by {}".format(
                    self.caused_object.consultation.patient.name,
                    self.caused_object.consultation.facility.name,
                    self.caused_by.get_full_name(),
                )
            elif self.event == Notification.Event.PATIENT_CONSULTATION_UPDATE_UPDATED.value:
                message = "Consultation for Patient {}  at facility {} was updated by {}".format(
                    self.caused_object.consultation.patient.name,
                    self.caused_object.consultation.facility.name,
                    self.caused_by.get_full_name(),
                )
        elif isinstance(self.caused_object, ShiftingRequest):
            if self.event == Notification.Event.SHIFTING_UPDATED.value:
                message = "Shifting for Patient {} was updated by {}".format(
                    self.caused_object.patient.name, self.caused_by.get_full_name(),
                )
        return message

    def generate_sms_message(self):
        message = ""
        if isinstance(self.caused_object, ShiftingRequest):
            if self.event == Notification.Event.SHIFTING_UPDATED.value:
                message = "Your Shifting Request to {} has been approved in Care. Please contact {} for any queries".format(
                    self.caused_object.assigned_facility.name,
                    self.caused_object.shifting_approving_facility.phone_number,
                )
        return message

    def _get_default_whatsapp_config(self):
        return {
            Notification.Event.PATIENT_CONSULTATION_ASSIGNMENT.value: {
                "message": "You have been assigned to a new patient in care platform for specialist teleconsultation.",
                "header": "Specialist Consultation Requested",
                "footer": "Click the following to link to view patient details.",
            }
        }

    def generate_whatsapp_message(self):
        if settings.WHATSAPP_MESSAGE_CONFIG:
            message_dict = json.loads(settings.WHATSAPP_MESSAGE_CONFIG)
        else:
            message_dict = self._get_default_whatsapp_config()
        return message_dict[self.event]

    def generate_sms_phone_numbers(self):
        if isinstance(self.caused_object, ShiftingRequest):
            return [
                self.caused_object.refering_facility_contact_number,
                self.caused_object.patient.phone_number,
                self.caused_object.patient.emergency_phone_number,
            ]

    def _get_default_medium(self):
        return [Notification.Medium.SYSTEM.value]

    def generate_cause_objects(self):
        if isinstance(self.caused_object, PatientRegistration):
            self.caused_objects["patient"] = str(self.caused_object.external_id)
            if self.caused_object.facility:
                self.caused_objects["facility"] = str(self.caused_object.facility.external_id)
        if isinstance(self.caused_object, PatientConsultation):
            self.caused_objects["consultation"] = str(self.caused_object.external_id)
            self.caused_objects["patient"] = str(self.caused_object.patient.external_id)
            if self.caused_object.patient.facility:
                self.caused_objects["facility"] = str(self.caused_object.patient.facility.external_id)
        if isinstance(self.caused_object, InvestigationSession):
            self.caused_objects["consultation"] = str(self.extra_data["consultation"].external_id)
            self.caused_objects["patient"] = str(self.extra_data["consultation"].patient.external_id)
            if self.extra_data["consultation"].patient.facility:
                self.caused_objects["facility"] = str(self.extra_data["consultation"].patient.facility.external_id)
            self.caused_objects["session"] = str(self.caused_object.external_id)
        if isinstance(self.caused_object, InvestigationValue):
            self.caused_objects["consultation"] = str(self.caused_object.consultation.external_id)
            self.caused_objects["patient"] = str(self.caused_object.consultation.patient.external_id)
            if self.caused_object.consultation.patient.facility:
                self.caused_objects["facility"] = str(self.caused_object.consultation.patient.facility.external_id)
            self.caused_objects["session"] = str(self.caused_object.session.external_id)
            self.caused_objects["investigation"] = str(self.caused_object.investigation.external_id)
        if isinstance(self.caused_object, DailyRound):
            self.caused_objects["consultation"] = str(self.caused_object.consultation.external_id)
            self.caused_objects["patient"] = str(self.caused_object.consultation.patient.external_id)
            self.caused_objects["daily_round"] = str(self.caused_object.id)
            if self.caused_object.consultation.patient.facility:
                self.caused_objects["facility"] = str(self.caused_object.consultation.facility.external_id)
        if isinstance(self.caused_object, ShiftingRequest):
            self.caused_objects["shifting"] = str(self.caused_object.external_id)

        return True

    def generate_whatsapp_users(self):
        if self.event == Notification.Event.PATIENT_CONSULTATION_ASSIGNMENT.value:
            return [self.caused_object.assigned_to]
        raise Exception("Action Does not have associated users")

    def generate_system_users(self):
        users = []
        extra_users = self.extra_users
        caused_user = self.caused_by
        facility_users = FacilityUser.objects.filter(facility_id=self.facility.id)
        for facility_user in facility_users:
            if facility_user.user.id != caused_user.id:
                users.append(facility_user.user)
        for user_id in extra_users:
            user_obj = User.objects.get(id=user_id)
            if user_obj.id != caused_user.id:
                users.append(user_obj)
        return users

    def generate_message_for_user(self, user, message, medium):
        notification = Notification()
        notification.intended_for = user
        notification.caused_objects = self.caused_objects
        notification.message = message
        notification.medium_sent = medium
        notification.event = self.event
        notification.event_type = self.event_type
        notification.caused_by = self.caused_by
        notification.save()
        return notification

    def send_webpush_user(self, user, message):
        try:
            if user.pf_endpoint and user.pf_p256dh and user.pf_auth:
                webpush(
                    subscription_info={
                        "endpoint": user.pf_endpoint,
                        "keys": {"p256dh": user.pf_p256dh, "auth": user.pf_auth},
                    },
                    data=message,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": "mailto:info@coronasafe.network",},
                )
        except WebPushException as ex:
            print("Web Push Failed with Exception: {}", repr(ex))
            if ex.response and ex.response.json():
                extra = ex.response.json()
                print(
                    "Remote service replied with a {}:{}, {}", extra.code, extra.errno, extra.message,
                )
        except Exception as e:
            print("Error When Doing WebPush", e)

    def generate(self):
        if not self.worker_initiated:
            return
        for medium in self.notification_mediums:
            if medium == Notification.Medium.SMS.value and settings.SEND_SMS_NOTIFICATION:
                sendSMS(self.generate_sms_phone_numbers(), self.generate_sms_message(), many=True)
            elif medium == Notification.Medium.SYSTEM.value:
                if not self.message:
                    self.message = self.generate_system_message()
                for user in self.generate_system_users():
                    notification_obj = self.generate_message_for_user(
                        user, self.message, Notification.Medium.SYSTEM.value
                    )
                    if not self.defer_notifications:
                        self.send_webpush_user(
                            user, json.dumps({"external_id": str(notification_obj.external_id), "title": self.message})
                        )
            elif medium == Notification.Medium.WHATSAPP.value and settings.ENABLE_WHATSAPP:
                for user in self.generate_whatsapp_users():
                    number = user.alt_phone_number
                    notification_obj = self.generate_message_for_user(
                        user, message, Notification.Medium.WHATSAPP.value
                    )
                    message = self.generate_whatsapp_message()
                    sendWhatsappMessage(number, message, notification_obj.external_id)

