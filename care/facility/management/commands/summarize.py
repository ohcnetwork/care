from django.core.management.base import BaseCommand

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import FacilityCapacity, FacilityRelatedSummary

from care.facility.summarisation.facility_capacity import FacilityCapacitySummary
from care.facility.summarisation.patient_summary import PatientSummary

from care.facility.summarisation.district.patient_summary import DistrictPatientSummary


class Command(BaseCommand):
    """
    Management command to Force Create Summary objects.
    """

    help = "Force Create Summary Objects"

    def handle(self, *args, **options):
        PatientSummary()
        print("Patients Summarised")
        FacilityCapacitySummary()
        print("Capacity Summarised")
        DistrictPatientSummary()
        print("District Wise Patient Summarised")

