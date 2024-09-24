from django.core.management.base import BaseCommand

from care.facility.utils.summarization.district.patient_summary import (
    district_patient_summary,
)
from care.facility.utils.summarization.facility_capacity import (
    facility_capacity_summary,
)
from care.facility.utils.summarization.patient_summary import patient_summary


class Command(BaseCommand):
    """
    Management command to Force Create Summary objects.
    """

    help = "Force Create Summary Objects"

    def handle(self, *args, **options):
        patient_summary()
        print("Patients Summarised")
        facility_capacity_summary()
        print("Capacity Summarised")
        district_patient_summary()
        print("District Wise Patient Summarised")
