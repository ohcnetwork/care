from django.core.management.base import BaseCommand

from care.facility.utils.summarisation.district.patient_summary import (
    district_patient_summary,
)
from care.facility.utils.summarisation.facility_capacity import (
    facility_capacity_summary,
)
from care.facility.utils.summarisation.patient_summary import patient_summary


class Command(BaseCommand):
    """
    Management command to Force Create Summary objects.
    """

    help = "Force Create Summary Objects"  # noqa: A003

    def handle(self, *args, **options):
        patient_summary()
        self.stdout.write(self.style.SUCCESS("Patients Summarized"))
        facility_capacity_summary()
        self.stdout.write(self.style.SUCCESS("Capacity Summarized"))
        district_patient_summary()
        self.stdout.write(self.style.SUCCESS("District Wise Patient Summarized"))
