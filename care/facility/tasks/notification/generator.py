import celery

from care.facility.models.facility import FacilityUser
from care.facility.models.notification import Notification


@celery.task()
def generate_notifications_for_facility(facility_id, data, defer_notifications):

    facility_users = FacilityUser.objects.filter(facility_id=facility_id)
    notifications = []
    for facility_user in facility_users:
        notifications.append(generate_message_for_user(facility_user.user, data.copy()))
    Notification.objects.bulk_create(notifications)
    if not defer_notifications:
        pass
        # Delay task to send notifications


def generate_message_for_user(user, data):
    data["intended_for_id"] = user.id
    return Notification(**data)
