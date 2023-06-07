import boto3
from django.conf import settings

from care.users.models import phone_number_regex


def sendSMS(phone_numbers, message, many=False):
    if not many:
        phone_numbers = [phone_numbers]
    phone_numbers = list(set(phone_numbers))
    for phone in phone_numbers:
        try:
            phone_number_regex(phone)
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
