import json
from datetime import datetime

import requests
from django.conf import settings


def _get_default_whatsapp_config():
    return {
        "admin_report": {
            "message": "Coronasafe Network",
            "header": "Daily summary auto-generated from care.",
            "footer": "Coronasafe Network",
        }
    }


def generate_whatsapp_message(object_name, public_url, phone_number):
    if settings.WHATSAPP_MESSAGE_CONFIG:
        message_dict = json.loads(settings.WHATSAPP_MESSAGE_CONFIG)
    else:
        message_dict = _get_default_whatsapp_config()
    message = message_dict["admin_report"]
    message["document"] = public_url
    message["file_name"] = f"{object_name}-{datetime.now().date()}.pdf"
    return _send(message, phone_number)


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


def _send(message, phone_number):
    _opt_in(phone_number)
    url_data = {
        "method": "SendMediaMessage",
        "auth_scheme": "plain",
        "v": "1.1",
        "send_to": phone_number,
        "msg": message["message"],
        "isHSM": "True",
        # "buttonUrlParam": str(notification_id),
        "msg_type": "DOCUMENT",
        "media_url": message["document"],
        "password": settings.WHATSAPP_API_PASSWORD,
        "userid": settings.WHATSAPP_API_USERNAME,
        "isTemplate": "true",
        "caption": message["header"],
        "footer": message["footer"],
        "filename": message["file_name"],
    }
    resp = requests.post(settings.WHATSAPP_API_ENDPOINT, params=url_data)
    return resp

