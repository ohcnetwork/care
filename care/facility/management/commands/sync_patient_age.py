
from datetime import date
from django.core.management.base import BaseCommand
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.exceptions import ValidationError

from care.facility.models import PatientRegistration



class Command(BaseCommand):
    """
    Management command to sync Date of Birth and Year of Birth and Age.
    """

    help = "Syncs the age of Patients based on Date of Birth and Year of Birth"

    def handle(self, *args, **options):
        qs = PatientRegistration.objects.all()
        failed = 0
        today = date.today()
        age = None
        for patient in qs:
            try:
                date_of_birth = patient.date_of_birth
                year_of_birth = patient.year_of_birth
                patient_file_age = patient.age
                if date_of_birth:
                    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day)) 
                elif year_of_birth:
                    age = today.year - year_of_birth
                elif patient_file_age:
                    patient.year_of_birth = today.year - patient_file_age
                    age = patient_file_age
                print(date_of_birth , year_of_birth , patient_file_age , age)
            except Exception:
                failed += 1
        if failed:
            print(f"Failed for {failed} Patient")
        else:
            print("Successfully Synced Age")
