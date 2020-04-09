import json
from typing import Optional

import phonenumbers
from django.core.management.base import BaseCommand
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.exceptions import ValidationError

from care.facility.models import PatientRegistration


def to_phone_number_field(phone_number):
    try:
        return PhoneNumberField().to_internal_value(phone_number)
    except ValidationError:
        parsed = phonenumbers.parse(phone_number, region="IN")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class Command(BaseCommand):
    """
    Management command to clean the phone number field of patient to support E164 format.
    """

    help = "Cleans the phone number field of patient to support E164 field"

    def handle(self, *args, **options) -> Optional[str]:
        qs = PatientRegistration.objects.all()
        failed = []
        for patient in qs:
            try:
                patient.phone_number = to_phone_number_field(patient.phone_number)
                patient.save()
            except Exception:
                failed.append({"id": patient.id, "phone_number": patient.phone_number})

        print(f"Completed for {qs.count()} | Failed for {len(failed)}")
        print(f"Failed for {json.dumps(failed)}")
