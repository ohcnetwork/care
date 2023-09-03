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

    help = (  # noqa: A003
        "Cleans the phone number field of patient to support E164 field"
    )

    def handle(self, *args, **options) -> str | None:
        qs = PatientRegistration.objects.all()
        failed = []
        for patient in qs:
            try:
                patient.phone_number = to_phone_number_field(patient.phone_number)
                patient.save()
            except Exception:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to clean phone number for {patient.id} {patient.phone_number}",
                    ),
                )

        if failed:
            self.stdout.write(
                self.style.ERROR(f"Failed to sync {len(failed)} patients"),
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully Synced {qs.count() - len(failed)} patients",
            ),
        )
