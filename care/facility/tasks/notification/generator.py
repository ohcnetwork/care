import celery
from django.conf import settings
from pywebpush import WebPushException, webpush

from care.facility.models.facility import FacilityUser
from care.facility.models.notification import Notification
from care.facility.models.patient import PatientRegistration
from care.users.models import User
from care.utils.sms.sendSMS import sendSMS


@celery.task()
def generate_sms_for_user(phone_numbers, message):
    sendSMS(phone_numbers, message, many=True)


@celery.task()
def generate_notifications_for_facility(facility_id, data, defer_notifications):
    extra_users = data.get("extra_users", [])
    del data["extra_users"]
    caused_user_id = data.get("caused_by_id", None)
    caused_user = None
    if caused_user_id:
        caused_user = User.objects.get(id=caused_user_id)
    facility_users = FacilityUser.objects.filter(facility_id=facility_id)
    # notifications = []
    for facility_user in facility_users:
        if facility_user.user.id != caused_user.id:
            generate_message_for_user(facility_user.user, data.copy())
            if not defer_notifications:
                send_webpush_user(facility_user.user, data["message"])
    for user_id in extra_users:
        user_obj = User.objects.get(id=user_id)
        if user_obj.id != caused_user.id:
            generate_message_for_user(user_obj, data.copy())
            if not defer_notifications:
                send_webpush_user(user_obj, data["message"])
    # Notification.objects.bulk_create(notifications)
    # for facility_user in facility_users:
    #     if not defer_notifications:
    #         pass
    #         # Delay task to send notifications


def send_webpush_user(user, message):
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


def generate_message_for_user(user, data):
    data["intended_for_id"] = user.id
    return Notification(**data).save()
