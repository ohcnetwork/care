import requests
from django.conf import settings

from care.users.models import phone_number_regex


def _opt_in(phone_number):
    url_data = {
        "method": "OPT_IN",
        "auth_scheme": "plain",
        "v": "1.1",
        "phone_number": phone_number,
        "password": settings.WHATSAPP_API_PASSWORD,
        "userid": settings.WHATSAPP_API_USERNAME,
        "channel": "whatsapp",
    }
    resp = requests.post(settings.WHATSAPP_API_ENDPOINT, params=url_data)
    return resp


def _send(phone_number, message):
    _opt_in(phone_number)
    url_data = {
        "method": "SendMessage",
        "auth_scheme": "plain",
        "v": "1.1",
        "send_to": phone_number,
        "msg": message,
        "isHSM": "True",
        "buttonUrlParam": "bDQ2NTkz",
        "msg_type": "HSM",
        "password": settings.WHATSAPP_API_PASSWORD,
        "userid": settings.WHATSAPP_API_USERNAME,
        "isTemplate": "true",
        "header": "Specialist Consultation Requested",
        "footer": "Click the following to link to view patient details.",
    }
    resp = requests.post(settings.WHATSAPP_API_ENDPOINT, params=url_data)
    return resp


def sendMessage(phone_numbers, message, many=False):
    if not many:
        phone_numbers = [phone_numbers]
    phone_numbers = list(set(phone_numbers))
    for phone in phone_numbers:
        try:
            phone_number_regex(phone)
        except Exception:
            continue
        _send(phone, message)
    return True
