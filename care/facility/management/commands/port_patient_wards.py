from datetime import date
from django.core.management.base import BaseCommand
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.exceptions import ValidationError

from care.facility.models import PatientRegistration

from care.users.models import Ward


class Command(BaseCommand):
    """
    Management command to sync Date of Birth and Year of Birth and Age.
    """

    help = "Syncs the age of Patients based on Date of Birth and Year of Birth"

    def handle(self, *args, **options):
        qs = PatientRegistration.objects.all()
        failed = 0
        success = 0
        for patient in qs:
            try:
                old_ward = patient.ward_old
                if not old_ward:
                    continue
                local_body = patient.local_body
                ward_object = Ward.objects.filter(local_body=local_body, number=old_ward).first()
                if ward_object is None:
                    failed += 1
                else:
                    success += 1
                    patient.ward = ward_object
                    patient.save()
            except Exception as e:
                failed += 1
        print(str(failed), " failed operations ", str(success), " sucessfull operations")

