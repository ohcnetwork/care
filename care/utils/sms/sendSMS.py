from typing import List

import boto3
from django.conf import settings
from sms import Message
from sms.backends.base import BaseSmsBackend

from care.utils.models.validators import mobile_validator


def sendSMS(phone_numbers, message, many=False):
    if not many:
        phone_numbers = [phone_numbers]
    phone_numbers = list(set(phone_numbers))
    for phone in phone_numbers:
        try:
            mobile_validator(phone)
        except Exception:
            continue
        client = boto3.client(
            "sns",
            aws_access_key_id=settings.SNS_ACCESS_KEY,
            aws_secret_access_key=settings.SNS_SECRET_KEY,
            region_name=settings.SNS_REGION,
        )
        client.publish(PhoneNumber=phone, Message=message)
    return True


class CustomSMSBackendSNS(BaseSmsBackend):
    def send_messages(self, messages: List[Message]):
        client = boto3.client(
            "sns",
            aws_access_key_id=settings.SNS_ACCESS_KEY,
            aws_secret_access_key=settings.SNS_SECRET_KEY,
            region_name=settings.SNS_REGION,
        )
        for message in messages:
            for phone_number in message.recipients:
                message_body = message.body

                try:
                    mobile_validator(phone_number)
                except Exception:
                    continue

                client.publish(PhoneNumber=phone_number, Message=message_body)

        return len(messages)
