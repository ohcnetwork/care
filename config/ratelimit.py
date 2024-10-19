import requests
from django.conf import settings
from django_ratelimit.core import is_ratelimited

VALIDATE_CAPTCHA_REQUEST_TIMEOUT = 5


def get_ratelimit_key(group, request):
    return "ratelimit"


def validatecaptcha(request):
    recaptcha_response = request.data.get(settings.GOOGLE_CAPTCHA_POST_KEY)
    if not recaptcha_response:
        return False
    values = {
        "secret": settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        "response": recaptcha_response,
    }
    captcha_response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data=values,
        timeout=VALIDATE_CAPTCHA_REQUEST_TIMEOUT,
    )
    result = captcha_response.json()

    return bool(result["success"])


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

    requests, time = rate_limit.split("/")

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
