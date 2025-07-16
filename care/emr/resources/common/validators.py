import datetime

from django.utils.timezone import is_aware, make_aware

from care.utils.time_util import care_now


def validate_datetime(dt: datetime.datetime) -> datetime.datetime:
    if dt:
        if not is_aware(dt):
            dt = make_aware(dt)
        if dt > care_now():
            raise ValueError("Date cannot be in the future")
    return dt
