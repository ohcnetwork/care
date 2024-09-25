import logging

import boto3
from django.conf import settings

from care.utils.models.validators import mobile_validator

logger = logging.getLogger(__name__)


def send_sms(phone_numbers, message, many=False):
    if not many:
        phone_numbers = [phone_numbers]
    phone_numbers = list(set(phone_numbers))
    for phone in phone_numbers:
        try:
            mobile_validator(phone)
        except Exception:
            if settings.DEBUG:
                logger.error("Invalid Phone Number %s", phone)
            continue
        client = boto3.client(
            "sns",
            aws_access_key_id=settings.SNS_ACCESS_KEY,
            aws_secret_access_key=settings.SNS_SECRET_KEY,
            region_name=settings.SNS_REGION,
        )
        client.publish(PhoneNumber=phone, Message=message)
    return True
