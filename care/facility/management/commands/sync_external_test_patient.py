from django.core.management.base import BaseCommand

from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_external_test import PatientExternalTest


class Command(BaseCommand):
    """
    Management command to Sync the patient created flag in external tests.
    """

    help = "Sync the patient created flag in external tests"

    def handle(self, *args, **options):
        print("Starting Sync")
        for patient in PatientRegistration.objects.all():
            if patient.srf_id:
                PatientExternalTest.objects.filter(srf_id__iexact=patient.srf_id).update(patient_created=True)
        print("Completed Sync")
