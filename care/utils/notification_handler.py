from care.facility.models.notification import Notification
from care.facility.models.facility import FacilityUser, Facility
from care.users.models import User


class NotificationCreationException(Exception):
    pass


class NotificationGenerator:
    def __init__(
        self,
        event_type=Notification.EventType.SYSTEM_GENERATED,
        event=None,
        caused_by=None,
        caused_object_external_id=None,
        message=None,
        defer_notifications=False,
    ):
        if not isinstance(event_type, Notification.EventType):
            raise NotificationCreationException("Event Type Invalid")
        if not isinstance(event, Notification.Event):
            raise NotificationCreationException("Event Invalid")
        if not isinstance(caused_by, User):
            raise NotificationCreationException(
                "edited_by must be an instance of a user"
            )
        self.event_type = event_type.value
        self.event = event.value
        self.caused_by = caused_by
        self.caused_object_external_id = caused_object_external_id
        self.message = message
        self.defer_notifications = defer_notifications

    def generate_notifications_for_facility(self, facility):
        if not isinstance(facility, Facility):
            raise NotificationCreationException(
                "facility must be an instance of Facility"
            )
        facility_users = FacilityUser.objects.filter(facility=facility)
        for facility_user in facility_users:
            self.generate_message_for_user(facility_user.user)
        if not self.defer_notifications:
            pass
            # Delay task to send notifications

    def generate_message_for_user(self, user):
        Notification(
            intended_for=user,
            caused_by=self.caused_by,
            event=self.event,
            event_type=self.event_type,
            message=self.message,
            caused_object_external_id=self.caused_object_external_id,
        ).save()
        return True
