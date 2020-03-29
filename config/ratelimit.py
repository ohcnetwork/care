from ratelimit.utils import is_ratelimited

from django.conf import settings

import requests


def validatecaptcha(request):
    recaptcha_response = request.POST.get(settings.GOOGLE_CAPTCHA_POST_KEY)
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


def ratelimit(request, group="", keys=[None], increment=True):
    checkcaptcha = False
    for key in keys:
        if key == 'ip':
            group = group
            key = 'ip'
        else:
            group = group + "-{}".format(key)
            key = settings.GETKEY
        if is_ratelimited(
            request,
            group=group,
            key=key,
            rate=settings.DJANGO_RATE_LIMIT,
            increment=True,
        ):
            checkcaptcha = True

    if checkcaptcha:
        if not validatecaptcha(request):
            return True
        else:
            return False

    return False
