import json
import logging

from celery import shared_task
from django.apps import apps
from django.conf import settings
from pywebpush import WebPushException, webpush

from care.facility.models.daily_round import DailyRound
from care.facility.models.facility import Facility, FacilityUser
from care.facility.models.notification import Notification
from care.facility.models.patient import PatientNotes, PatientRegistration
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.models.patient_investigation import (
    InvestigationSession,
    InvestigationValue,
)
from care.facility.models.shifting import ShiftingRequest
from care.users.models import User
from care.utils.sms.send_sms import send_sms

logger = logging.getLogger(__name__)


class NotificationCreationError(Exception):
    pass


@shared_task
def notification_task_generator(**kwargs):
    NotificationGenerator(**kwargs).generate()


@shared_task
def send_webpush(**kwargs):
    user = User.objects.get(username=kwargs.get("username"))
    message = kwargs.get("message")
    NotificationGenerator.send_webpush_user(None, user, message)


def get_model_class(model_name):
    if model_name == "User":
        return apps.get_model(f"users.{model_name}")
    return apps.get_model(f"facility.{model_name}")


# ruff: noqa: SIM102, PLR0912 rebuilding the notification generator would be easier
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
                msg = "Event Type Invalid"
                raise NotificationCreationError(msg)
            if not isinstance(event, Notification.Event):
                msg = "Event Invalid"
                raise NotificationCreationError(msg)
            if not isinstance(caused_by, User):
                msg = "edited_by must be an instance of a user"
                raise NotificationCreationError(msg)
            if facility and not isinstance(facility, Facility):
                msg = "facility must be an instance of Facility"
                raise NotificationCreationError(msg)
            mediums = []
            if notification_mediums:
                for medium in notification_mediums:
                    if not isinstance(medium, Notification.Medium):
                        msg = "Medium Type Invalid"
                        raise NotificationCreationError(msg)
                    mediums.append(medium.value)
            data = {
                "event_type": event_type.value,
                "event": event.value,
                "caused_by": caused_by.id,
                "caused_object": caused_object.__class__.__name__,
                "caused_object_pk": caused_object.id,
                "message": message,
                "defer_notifications": defer_notifications,
                "generate_for_facility": generate_for_facility,
                "extra_users": extra_users,
                "extra_data": self.serialize_extra_data(extra_data),
                "notification_mediums": mediums,
                "worker_initated": True,
            }
            if facility:
                data["facility"] = facility.id
            notification_task_generator.apply_async(kwargs=data, countdown=2)
            self.worker_initiated = False
            return
        self.worker_initiated = True
        caused_object = get_model_class(caused_object).objects.get(id=caused_object_pk)
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
            extra_data[key] = {
                "model_name": extra_data[key].__class__.__name__,
                "model_id": extra_data[key].id,
            }
        return extra_data

    def deserialize_extra_data(self, extra_data):
        if not extra_data:
            return None
        for key in extra_data:
            extra_data[key] = apps.get_model(
                "facility.{}".format(extra_data[key]["model_name"])
            ).objects.get(id=extra_data[key]["model_id"])
        return extra_data

    def generate_extra_users(self):
        if isinstance(self.caused_object, PatientConsultation):
            if self.caused_object.assigned_to:
                self.extra_users.append(self.caused_object.assigned_to.id)
        if isinstance(self.caused_object, PatientRegistration):
            if self.caused_object.last_consultation:
                if self.caused_object.last_consultation.assigned_to:
                    self.extra_users.append(
                        self.caused_object.last_consultation.assigned_to.id
                    )
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
                message = f"Patient {self.caused_object.name} was created by {self.caused_by.get_full_name()}"
            elif self.event == Notification.Event.PATIENT_UPDATED.value:
                message = f"Patient {self.caused_object.name} was updated by {self.caused_by.get_full_name()}"
            if self.event == Notification.Event.PATIENT_DELETED.value:
                message = f"Patient {self.caused_object.name} was deleted by {self.caused_by.get_full_name()}"
            if self.event == Notification.Event.PATIENT_FILE_UPLOAD_CREATED.value:
                message = f"A file for patient {self.caused_object.name} was uploaded by {self.caused_by.get_full_name()}"
        elif isinstance(self.caused_object, PatientConsultation):
            if self.event == Notification.Event.PATIENT_CONSULTATION_CREATED.value:
                message = f"Consultation for Patient {self.caused_object.patient.name} was created by {self.caused_by.get_full_name()}"
            elif self.event == Notification.Event.PATIENT_CONSULTATION_UPDATED.value:
                message = f"Consultation for Patient {self.caused_object.patient.name} was updated by {self.caused_by.get_full_name()}"
            if self.event == Notification.Event.PATIENT_CONSULTATION_DELETED.value:
                message = f"Consultation for Patient {self.caused_object.patient.name} was deleted by {self.caused_by.get_full_name()}"
            if self.event == Notification.Event.CONSULTATION_FILE_UPLOAD_CREATED.value:
                message = f"Consultation file for Patient {self.caused_object.patient.name} was uploaded by {self.caused_by.get_full_name()}"
            if self.event == Notification.Event.PATIENT_PRESCRIPTION_CREATED.value:
                message = f"Prescription for Patient {self.caused_object.patient.name} was created by {self.caused_by.get_full_name()}"
            if self.event == Notification.Event.PATIENT_PRESCRIPTION_UPDATED.value:
                message = f"Prescription for Patient {self.caused_object.patient.name} was updated by {self.caused_by.get_full_name()}"
        elif isinstance(self.caused_object, InvestigationSession):
            if self.event == Notification.Event.INVESTIGATION_SESSION_CREATED.value:
                message = (
                    "Investigation Session for Patient {} was created by {}".format(
                        self.extra_data["consultation"].patient.name,
                        self.caused_by.get_full_name(),
                    )
                )
        elif isinstance(self.caused_object, InvestigationValue):
            if self.event == Notification.Event.INVESTIGATION_UPDATED.value:
                message = f"Investigation Value for {self.caused_object.investigation.name} for Patient {self.caused_object.consultation.patient.name} was updated by {self.caused_by.get_full_name()}"
        elif isinstance(self.caused_object, DailyRound):
            if (
                self.event
                == Notification.Event.PATIENT_CONSULTATION_UPDATE_CREATED.value
            ):
                message = f"Consultation for Patient {self.caused_object.consultation.patient.name}  at facility {self.caused_object.consultation.facility.name} was created by {self.caused_by.get_full_name()}"
            elif (
                self.event
                == Notification.Event.PATIENT_CONSULTATION_UPDATE_UPDATED.value
            ):
                message = f"Consultation for Patient {self.caused_object.consultation.patient.name}  at facility {self.caused_object.consultation.facility.name} was updated by {self.caused_by.get_full_name()}"
        elif isinstance(self.caused_object, ShiftingRequest):
            if self.event == Notification.Event.SHIFTING_UPDATED.value:
                message = f"Shifting for Patient {self.caused_object.patient.name} was updated by {self.caused_by.get_full_name()}"
        elif isinstance(self.caused_object, PatientNotes):
            if self.event == Notification.Event.PATIENT_NOTE_ADDED.value:
                message = f"Notes for Patient {self.caused_object.patient.name} was added by {self.caused_by.get_full_name()}"

        return message

    def generate_sms_message(self):
        message = ""
        if isinstance(self.caused_object, ShiftingRequest):
            if self.event == Notification.Event.SHIFTING_UPDATED.value:
                message = f"Your Shifting Request to {self.caused_object.assigned_facility.name} has been approved in Care. Please contact {self.caused_object.shifting_approving_facility.phone_number} for any queries"
        return message

    def generate_sms_phone_numbers(self):
        if isinstance(self.caused_object, ShiftingRequest):
            return [
                self.caused_object.refering_facility_contact_number,
                self.caused_object.patient.phone_number,
                self.caused_object.patient.emergency_phone_number,
            ]
        return None

    def _get_default_medium(self):
        return [Notification.Medium.SYSTEM.value]

    def generate_cause_objects(self):
        if isinstance(self.caused_object, PatientRegistration):
            self.caused_objects["patient"] = str(self.caused_object.external_id)
            if self.caused_object.facility:
                self.caused_objects["facility"] = str(
                    self.caused_object.facility.external_id
                )
        if isinstance(self.caused_object, PatientConsultation):
            self.caused_objects["consultation"] = str(self.caused_object.external_id)
            self.caused_objects["patient"] = str(self.caused_object.patient.external_id)
            if self.caused_object.patient.facility:
                self.caused_objects["facility"] = str(
                    self.caused_object.patient.facility.external_id
                )
        if isinstance(self.caused_object, InvestigationSession):
            self.caused_objects["consultation"] = str(
                self.extra_data["consultation"].external_id
            )
            self.caused_objects["patient"] = str(
                self.extra_data["consultation"].patient.external_id
            )
            if self.extra_data["consultation"].patient.facility:
                self.caused_objects["facility"] = str(
                    self.extra_data["consultation"].patient.facility.external_id
                )
            self.caused_objects["session"] = str(self.caused_object.external_id)
        if isinstance(self.caused_object, InvestigationValue):
            self.caused_objects["consultation"] = str(
                self.caused_object.consultation.external_id
            )
            self.caused_objects["patient"] = str(
                self.caused_object.consultation.patient.external_id
            )
            if self.caused_object.consultation.patient.facility:
                self.caused_objects["facility"] = str(
                    self.caused_object.consultation.patient.facility.external_id
                )
            self.caused_objects["session"] = str(self.caused_object.session.external_id)
            self.caused_objects["investigation"] = str(
                self.caused_object.investigation.external_id
            )
        if isinstance(self.caused_object, DailyRound):
            self.caused_objects["consultation"] = str(
                self.caused_object.consultation.external_id
            )
            self.caused_objects["patient"] = str(
                self.caused_object.consultation.patient.external_id
            )
            self.caused_objects["daily_round"] = str(self.caused_object.external_id)
            if self.caused_object.consultation.patient.facility:
                self.caused_objects["facility"] = str(
                    self.caused_object.consultation.facility.external_id
                )
        if isinstance(self.caused_object, ShiftingRequest):
            self.caused_objects["shifting"] = str(self.caused_object.external_id)

        if isinstance(self.caused_object, PatientNotes):
            self.caused_objects["patient"] = str(self.caused_object.patient.external_id)
            self.caused_objects["facility"] = str(
                self.caused_object.facility.external_id
            )

        return True

    def generate_system_users(self):
        users = []
        extra_users = self.extra_users
        caused_user = self.caused_by
        facility_users = FacilityUser.objects.filter(facility_id=self.facility.id)
        if self.event != Notification.Event.MESSAGE:
            facility_users.exclude(
                user__user_type__in=(
                    User.TYPE_VALUE_MAP["Staff"],
                    User.TYPE_VALUE_MAP["StaffReadOnly"],
                )
            )
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
                    vapid_claims={
                        "sub": "mailto:info@ohc.network",
                    },
                )
        except WebPushException as ex:
            logger.info("Web Push Failed with Exception: %s", repr(ex))
            if ex.response and ex.response.json():
                extra = ex.response.json()
                logger.info(
                    "Remote service replied with a %s:%s, %s",
                    extra.code,
                    extra.errno,
                    extra.message,
                )
        except Exception as e:
            logger.info("Error When Doing WebPush: %s", e)

    def generate(self):
        if not self.worker_initiated:
            return
        for medium in self.notification_mediums:
            if (
                medium == Notification.Medium.SMS.value
                and settings.SEND_SMS_NOTIFICATION
            ):
                send_sms(
                    self.generate_sms_phone_numbers(),
                    self.generate_sms_message(),
                    many=True,
                )
            elif medium == Notification.Medium.SYSTEM.value:
                if not self.message:
                    self.message = self.generate_system_message()
                for user in self.generate_system_users():
                    notification_obj = self.generate_message_for_user(
                        user, self.message, Notification.Medium.SYSTEM.value
                    )
                    if not self.defer_notifications:
                        self.send_webpush_user(
                            user,
                            json.dumps(
                                {
                                    "external_id": str(notification_obj.external_id),
                                    "message": self.message,
                                    "type": Notification.Event(
                                        notification_obj.event
                                    ).name,
                                }
                            ),
                        )
