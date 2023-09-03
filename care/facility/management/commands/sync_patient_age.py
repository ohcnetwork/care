from django.core.management.base import BaseCommand

from care.facility.models import PatientRegistration


class Command(BaseCommand):
    """
    Management command to sync Date of Birth and Year of Birth and Age.
    """

    help = "Syncs the age of Patients based on Date of Birth and Year of Birth"  # noqa: A003

    def handle(self, *args, **options):
        qs = PatientRegistration.objects.all()
        failed = 0
        for patient in qs:
            try:
                patient.save()
            except Exception:
                failed += 1
        if failed:
            self.stdout.write(
                self.style.ERROR(f"Failed to Sync Age for {failed} Patients"),
            )
        else:
            self.stdout.write("Successfully Synced Age")
