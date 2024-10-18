from django.core.management.base import BaseCommand

from care.facility.models import PatientRegistration


class Command(BaseCommand):
    """
    Management command to sync Date of Birth and Year of Birth and Age.
    """

    help = "Syncs the age of Patients based on Date of Birth and Year of Birth"

    def handle(self, *args, **options):
        qs = PatientRegistration.objects.all()
        failed = 0
        for patient in qs:
            try:
                patient.save()
            except Exception:
                failed += 1
        if failed:
            self.stdout.write(f"Failed for {failed} Patient")
        else:
            self.stdout.write("Successfully Synced Age")
