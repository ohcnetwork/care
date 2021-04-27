import json
from django.core.management.base import BaseCommand
from care.facility.models.patient import PatientRegistration


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        qs = PatientRegistration.objects.all()
        qs.filter(disease_status=4).update(disease_status=5)

        print(f"Completed for {qs.count()}")
