from django.core.management import BaseCommand

from care.facility.models import PatientRegistration


class Command(BaseCommand):
    """
    copy data from countries_travelled_old to countries_travelled
    """

    def handle(self, **options):
        self.copy_countries_travelled_old()

    @staticmethod
    def copy_countries_travelled_old():
        patients = PatientRegistration.objects.filter(countries_travelled__isnull=True)
        for patient in patients:
            if patient.countries_travelled_old:
                patient.countries_travelled = patient.countries_travelled_old.split(",")
            else:
                patient.countries_travelled = []
            patient.save()
