import requests
from django.conf import settings
from care.users.models import phone_number_regex


def _send(phone_number, message):
    data = {
        "method": "SendMessage",
        "auth_scheme": "plain",
        "v": "1.1",
        "send_to": phone_number,
        "msg": message,
    }
    resp = requests.get(settings.WHATSAPP_API_ENDPOINT, data=data, auth=requests.auth.HTTPBasicAuth("user", "pass"))
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
