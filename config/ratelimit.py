import requests
from django.conf import settings
from django_ratelimit.core import is_ratelimited

CAPTCHA_VALIDATION_REQUEST_TIMEOUT = 25


def get_key(group, request):
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
        timeout=CAPTCHA_VALIDATION_REQUEST_TIMEOUT,
    )
    result = captcha_response.json()

    if result["success"] is True:
        return True
    return False


# refer https://django-ratelimit.readthedocs.io/en/stable/rates.html for rate
def ratelimit(
    request,
    group="",
    keys=None,
    rate=settings.DJANGO_RATE_LIMIT,
    increment=True,
):
    if keys is None:
        keys = [None]
    if settings.DISABLE_RATELIMIT:
        return False

    checkcaptcha = False
    for _key in keys:
        if _key == "ip":
            key = "ip"
        else:
            group = group + f"-{_key}"
            key = get_key
        if is_ratelimited(
            request,
            group=group,
            key=key,
            rate=rate,
            increment=increment,
        ):
            checkcaptcha = True

    if checkcaptcha:
        return bool(not validatecaptcha(request))

    return False
