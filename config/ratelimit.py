import struct

from altcha import Payload, verify_solution
from django.conf import settings
from django.core.cache import cache
from django_ratelimit.core import is_ratelimited

ALTCHA_PAYLOAD_MAX_LENGTH = 4096
ALTCHA_REPLAY_CACHE_TIMEOUT = 5 * 60
ALTCHA_VERIFIED_ATTRIBUTE = "altcha_verified"


def get_ratelimit_key(group, request):
    return "ratelimit"


def validatecaptcha(request):
    if getattr(request, ALTCHA_VERIFIED_ATTRIBUTE, False):
        return True

    altcha_payload = request.data.get(settings.ALTCHA_POST_KEY)
    if (
        not isinstance(altcha_payload, str)
        or len(altcha_payload) > ALTCHA_PAYLOAD_MAX_LENGTH
    ):
        return False

    try:
        payload = Payload.from_base64(altcha_payload)
        result = verify_solution(payload, settings.ALTCHA_HMAC_SECRET)
    except (KeyError, OverflowError, struct.error, TypeError, ValueError):
        return False

    if not result.verified or not payload.challenge.signature:
        return False

    if not cache.add(
        f"altcha-used:{payload.challenge.signature}",
        value=True,
        timeout=ALTCHA_REPLAY_CACHE_TIMEOUT,
    ):
        return False

    setattr(request, ALTCHA_VERIFIED_ATTRIBUTE, True)
    return True


# refer https://django-ratelimit.readthedocs.io/en/stable/rates.html for rate
def ratelimit(
    request, group="", keys=None, rate=settings.DJANGO_RATE_LIMIT, increment=True
):
    if keys is None:
        keys = [None]
    if settings.DISABLE_RATELIMIT:
        return False

    checkcaptcha = False
    for key in keys:
        if key == "ip":
            _group = group
            _key = "ip"
        else:
            _group = group + f"-{key}"
            _key = get_ratelimit_key
        if is_ratelimited(
            request,
            group=_group,
            key=_key,
            rate=rate,
            increment=increment,
        ):
            checkcaptcha = True

    if checkcaptcha:
        return not validatecaptcha(request)

    return False


def get_user_readable_rate_limit_time(rate_limit):
    if not rate_limit:
        return "1 second"

    _requests, time = rate_limit.split("/")

    time_unit_map = {
        "s": "second(s)",
        "m": "minute(s)",
        "h": "hour(s)",
        "d": "day(s)",
    }

    time_value = time[:-1]
    time_unit = time[-1]

    return f"{time_value or 1} {time_unit_map.get(time_unit, 'second(s)')}"


USER_READABLE_RATE_LIMIT_TIME = get_user_readable_rate_limit_time(
    settings.DJANGO_RATE_LIMIT
)
