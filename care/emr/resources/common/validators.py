import datetime

from django.utils.timezone import is_aware, make_aware

from care.utils.time_util import care_now


def validate_datetime(
    datetime: datetime.datetime,
) -> datetime.datetime:
    if datetime:
        if not is_aware(datetime):
            datetime = make_aware(datetime)
        if datetime > care_now():
            raise ValueError("Date cannot be in the future")
    return datetime
