import requests
from django.conf import settings
from django_ratelimit.core import is_ratelimited


def GETKEY(group, request):
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
        "https://www.google.com/recaptcha/api/siteverify", data=values
    )
    result = captcha_response.json()

    if result["success"] is True:
        return True
    return False


# refer https://django-ratelimit.readthedocs.io/en/stable/rates.html for rate
def ratelimit(
    request, group="", keys=[None], rate=settings.DJANGO_RATE_LIMIT, increment=True
):
    if settings.DISABLE_RATELIMIT:
        return False

    checkcaptcha = False
    for key in keys:
        if key == "ip":
            group = group
            key = "ip"
        else:
            group = group + f"-{key}"
            key = GETKEY
        if is_ratelimited(
            request,
            group=group,
            key=key,
            rate=rate,
            increment=increment,
        ):
            checkcaptcha = True

    if checkcaptcha:
        if not validatecaptcha(request):
            return True
        else:
            return False

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
