import datetime

from django.utils.timezone import is_aware, make_aware

from care.utils.time_util import care_now


def validate_onset_datetime_field(
    onset_datetime: datetime.datetime,
) -> datetime.datetime:
    if onset_datetime:
        if not is_aware(onset_datetime):
            onset_datetime = make_aware(onset_datetime)
        if onset_datetime > care_now():
            raise ValueError("Onset date cannot be in the future")
    return onset_datetime
